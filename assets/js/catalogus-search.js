(function () {
    "use strict";

    var root = document.querySelector("[data-catalogus-search]");
    if (!root || !window.CatalogusData) {
        return;
    }

    var form = root.querySelector("[data-search-form]");
    var queryInput = root.querySelector("[data-search-query]");
    var fieldFilter = root.querySelector("[data-field-filter]");
    var dateFrom = root.querySelector("[data-date-from]");
    var dateTo = root.querySelector("[data-date-to]");
    var repositoryFilter = root.querySelector("[data-repository-filter]");
    var status = root.querySelector("[data-search-status]");
    var results = root.querySelector("[data-search-results]");
    var searchIndexUrl = root.getAttribute("data-search-index-url");
    var manifestUrl = root.getAttribute("data-manifest-url");
    var baseUrl = root.getAttribute("data-base-url") || "";
    var documents = [];
    var manifest = null;
    var indexed = [];

    function selectedFieldText(doc) {
        var fields = doc.fields || {};
        switch (fieldFilter.value) {
        case "signature":
            return fields.signature || doc.signature || "";
        case "contents":
            if (doc.type !== "item" && doc.type !== "manuscript") { return ""; }
            return fields.titles || "";
        case "persons":
            if (doc.type !== "item" && doc.type !== "manuscript") { return ""; }
            return fields.persons || "";
        case "incipit":
            if (doc.type !== "item") { return ""; }
            return fields.incipits || "";
        case "german":
            return doc.type === "catalogue_de" ? fields.catalogue || "" : "";
        case "latin":
            return doc.type === "catalogue_la" ? fields.catalogue || "" : "";
        default:
            return Object.keys(fields).map(function (key) { return fields[key] || ""; }).join(" \n");
        }
    }

    function intervalsOverlap(intervals, fromYear, toYear) {
        if (!fromYear && !toYear) {
            return true;
        }
        if (!Array.isArray(intervals) || !intervals.length) {
            return false;
        }
        var from = fromYear || -Infinity;
        var to = toYear || Infinity;
        return intervals.some(function (interval) {
            return Number(interval.to) >= from && Number(interval.from) <= to;
        });
    }

    function matchesFilters(entry, terms) {
        var doc = entry.doc;
        if (repositoryFilter.value && doc.repository !== repositoryFilter.value) {
            return false;
        }
        var fromYear = parseInt(dateFrom.value, 10) || null;
        var toYear = parseInt(dateTo.value, 10) || null;
        if (fromYear && toYear && fromYear > toYear) {
            var tmp = fromYear; fromYear = toYear; toYear = tmp;
        }
        if (!intervalsOverlap(doc.dateIntervals, fromYear, toYear)) {
            return false;
        }
        if (!terms.length) {
            return true;
        }
        var haystack = CatalogusData.searchable(selectedFieldText(doc));
        return terms.every(function (term) { return haystack.indexOf(term) !== -1; });
    }

    function score(entry, terms, rawQuery) {
        var doc = entry.doc;
        var fields = entry.fields;
        var value = CatalogusData.normalize(rawQuery);
        var points = Number(doc.rank || 0);
        if (value && CatalogusData.normalize(doc.signature) === value) {
            points += 400;
        } else if (value && fields.signature.indexOf(value) !== -1) {
            points += 180;
        }
        terms.forEach(function (term) {
            if (fields.titles.indexOf(term) !== -1) { points += 30; }
            if (fields.incipits.indexOf(term) !== -1) { points += 24; }
            if (fields.persons.indexOf(term) !== -1) { points += 20; }
            if (fields.explicits.indexOf(term) !== -1) { points += 16; }
            if (fields.notes.indexOf(term) !== -1) { points += 9; }
        });
        if (fieldFilter.value !== "all") {
            points += 25;
        }
        return points;
    }

    function compareResults(a, b) {
        if (a.score !== b.score) {
            return b.score - a.score;
        }
        var sig = CatalogusData.naturalCompare(a.doc.signature, b.doc.signature);
        if (sig) { return sig; }
        if (a.doc.type !== b.doc.type) {
            return Number(b.doc.rank || 0) - Number(a.doc.rank || 0);
        }
        return CatalogusData.naturalCompare(a.doc.title, b.doc.title);
    }

    function search(rawQuery) {
        var terms = CatalogusData.queryTerms(rawQuery);
        return indexed
            .filter(function (entry) { return matchesFilters(entry, terms); })
            .map(function (entry) { return { doc: entry.doc, score: score(entry, terms, rawQuery), terms: terms }; })
            .sort(compareResults);
    }

    function bestSnippetSource(doc, terms) {
        var fields = doc.fields || {};
        var candidates;
        if (doc.type === "catalogue_de" || doc.type === "catalogue_la") {
            candidates = [{ label: doc.sourceLabel, value: fields.catalogue || "" }];
        } else {
            candidates = [
                { label: "Titel", value: fields.titles },
                { label: "Personen", value: fields.persons },
                { label: "Incipit", value: fields.incipits },
                { label: "Explicit", value: fields.explicits },
                { label: "Notiz", value: fields.notes },
                { label: "Physische Beschreibung", value: fields.physical }
            ];
        }
        for (var i = 0; i < candidates.length; i += 1) {
            if (!candidates[i].value) { continue; }
            var normalized = CatalogusData.searchable(candidates[i].value);
            if (!terms.length || terms.some(function (term) { return normalized.indexOf(term) !== -1; })) {
                return candidates[i];
            }
        }
        return null;
    }

    function makeSnippet(doc, terms) {
        var source = bestSnippetSource(doc, terms);
        if (!source || !source.value) { return null; }
        var value = CatalogusData.text(source.value).replace(/\s+/g, " ").trim();
        if (!value) { return null; }
        var normalized = CatalogusData.normalize(value);
        var first = -1;
        terms.forEach(function (term) {
            var index = normalized.indexOf(term);
            if (index !== -1 && (first === -1 || index < first)) { first = index; }
        });
        var start = first > 90 ? first - 90 : 0;
        var end = Math.min(value.length, start + 310);
        var snippet = value.slice(start, end);
        if (start > 0) { snippet = "…" + snippet; }
        if (end < value.length) { snippet += "…"; }
        return { label: source.label, text: snippet };
    }

    function detailHref(doc) {
        return baseUrl + doc.url + (doc.anchor || "");
    }

    function renderResults(found, rawQuery) {
        results.replaceChildren();
        var hasQuery = rawQuery.trim().length > 0;
        var hasFilters = Boolean(dateFrom.value || dateTo.value || repositoryFilter.value || fieldFilter.value !== "all");
        if (!hasQuery && !hasFilters) {
            status.textContent = manifest.recordCount + " Handschriften und " + manifest.itemCount + " strukturierte Inhaltseinheiten sind geladen. Bitte Suchbegriff eingeben oder Filter setzen.";
            return;
        }
        status.textContent = found.length + (found.length === 1 ? " Treffer" : " Treffer") + ".";
        if (!found.length) {
            var empty = document.createElement("p");
            empty.className = "catalogus-search-empty";
            empty.textContent = "Keine Treffer gefunden. Bei gesetztem Datumsfilter werden nur Handschriften mit numerisch normalisierter Entstehungsdatierung berücksichtigt.";
            results.appendChild(empty);
            return;
        }

        found.slice(0, 100).forEach(function (result) {
            var doc = result.doc;
            var article = document.createElement("article");
            article.className = "catalogus-result-card";

            var source = document.createElement("p");
            source.className = "catalogus-result-source";
            var badge = document.createElement("span");
            badge.className = "catalogus-badge";
            badge.textContent = doc.sourceLabel;
            source.appendChild(badge);
            article.appendChild(source);

            var heading = document.createElement("h3");
            var link = document.createElement("a");
            link.href = detailHref(doc);
            var titleText = doc.type === "item" ? doc.title : doc.signature + " — " + doc.title;
            CatalogusData.appendHighlightedText(link, titleText, result.terms);
            heading.appendChild(link);
            article.appendChild(heading);

            var meta = document.createElement("p");
            meta.className = "catalogus-result-meta";
            var metaParts = [];
            if (doc.type === "item") { metaParts.push(doc.signature); }
            if (doc.dateDisplay) { metaParts.push(doc.dateDisplay); }
            if (doc.locus) { metaParts.push(doc.locus); }
            if (doc.repository) { metaParts.push(doc.repository); }
            meta.textContent = metaParts.join(" · ");
            article.appendChild(meta);

            var snippetData = makeSnippet(doc, result.terms);
            if (snippetData && hasQuery) {
                var context = document.createElement("p");
                context.className = "catalogus-result-context";
                context.textContent = snippetData.label;
                article.appendChild(context);
                var snippet = document.createElement("p");
                snippet.className = "catalogus-result-snippet";
                CatalogusData.appendHighlightedText(snippet, snippetData.text, result.terms);
                article.appendChild(snippet);
            }

            var button = document.createElement("a");
            button.className = "button-link";
            button.href = detailHref(doc);
            button.textContent = doc.type === "item" ? "Zur Inhaltseinheit" : "Zur Handschrift";
            article.appendChild(button);
            results.appendChild(article);
        });

        if (found.length > 100) {
            var note = document.createElement("p");
            note.className = "catalogus-pagination-note";
            note.textContent = "Die ersten 100 Treffer werden angezeigt. Bitte Suche oder Filter weiter eingrenzen.";
            results.appendChild(note);
        }
    }

    function runSearch() {
        renderResults(search(queryInput.value), queryInput.value);
    }

    function populateRepositories() {
        Object.keys(manifest.repositories || {}).sort(CatalogusData.naturalCompare).forEach(function (name) {
            var option = document.createElement("option");
            option.value = name;
            option.textContent = name + " (" + manifest.repositories[name] + ")";
            repositoryFilter.appendChild(option);
        });
    }

    function initialize(payloads) {
        manifest = payloads[0];
        documents = payloads[1].documents || [];
        indexed = documents.map(function (doc) {
            var fields = doc.fields || {};
            return {
                doc: doc,
                fields: {
                    signature: CatalogusData.searchable(fields.signature || doc.signature),
                    titles: CatalogusData.searchable(fields.titles || ""),
                    persons: CatalogusData.searchable(fields.persons || ""),
                    incipits: CatalogusData.searchable(fields.incipits || ""),
                    explicits: CatalogusData.searchable(fields.explicits || ""),
                    notes: CatalogusData.searchable(fields.notes || ""),
                    physical: CatalogusData.searchable(fields.physical || "")
                }
            };
        });
        populateRepositories();
        status.textContent = manifest.recordCount + " Handschriften und " + manifest.itemCount + " strukturierte Inhaltseinheiten sind geladen. Bitte Suchbegriff eingeben oder Filter setzen.";

        var params = new URLSearchParams(window.location.search);
        if (params.get("q")) { queryInput.value = params.get("q"); }
        if (params.get("field")) { fieldFilter.value = params.get("field"); }
        if (params.get("from")) { dateFrom.value = params.get("from"); }
        if (params.get("to")) { dateTo.value = params.get("to"); }
        if (params.get("repository")) { repositoryFilter.value = params.get("repository"); }
        if (queryInput.value || dateFrom.value || dateTo.value || repositoryFilter.value || fieldFilter.value !== "all") {
            runSearch();
        }
    }

    function updateUrlAndSearch(event) {
        if (event) { event.preventDefault(); }
        var params = new URLSearchParams();
        if (queryInput.value.trim()) { params.set("q", queryInput.value.trim()); }
        if (fieldFilter.value !== "all") { params.set("field", fieldFilter.value); }
        if (dateFrom.value) { params.set("from", dateFrom.value); }
        if (dateTo.value) { params.set("to", dateTo.value); }
        if (repositoryFilter.value) { params.set("repository", repositoryFilter.value); }
        var query = params.toString();
        window.history.replaceState(null, "", window.location.pathname + (query ? "?" + query : ""));
        runSearch();
    }

    form.addEventListener("submit", updateUrlAndSearch);
    fieldFilter.addEventListener("change", updateUrlAndSearch);
    repositoryFilter.addEventListener("change", updateUrlAndSearch);
    dateFrom.addEventListener("change", updateUrlAndSearch);
    dateTo.addEventListener("change", updateUrlAndSearch);

    Promise.all([
        CatalogusData.loadJson(manifestUrl, "Catalogus-Manifest konnte nicht geladen werden."),
        CatalogusData.loadJson(searchIndexUrl, "Catalogus-Suchindex konnte nicht geladen werden.")
    ]).then(initialize).catch(function (error) {
        status.textContent = error.message;
        status.classList.add("catalogus-loading-error");
    });
}());
