(function () {
    "use strict";

    var root = document.querySelector("[data-catalogus-search]");
    if (!root || !window.CatalogusData) {
        return;
    }

    var form = root.querySelector("[data-search-form]");
    var queryInput = root.querySelector("[data-search-query]");
    var fieldFilter = root.querySelector("[data-field-filter]");
    var entityFilter = root.querySelector("[data-entity-filter]");
    var dateFrom = root.querySelector("[data-date-from]");
    var dateTo = root.querySelector("[data-date-to]");
    var repositoryFilter = root.querySelector("[data-repository-filter]");
    var status = root.querySelector("[data-search-status]");
    var resultEntityFilters = root.querySelector("[data-result-entity-filters]");
    var results = root.querySelector("[data-search-results]");
    var searchIndexUrl = root.getAttribute("data-search-index-url");
    var manifestUrl = root.getAttribute("data-manifest-url");
    var baseUrl = root.getAttribute("data-base-url") || "";
    var documents = [];
    var manifest = null;
    var indexed = [];
    var activeResultEntity = "all";
    var lastFound = [];
    var lastRawQuery = "";

    var fallbackEntityOrder = [
        "codex", "content", "physical_unit", "person", "incipit",
        "explicit_colophon", "addition", "catalogue"
    ];

    var fallbackEntityLabels = {
        codex: "Codex",
        content: "Werk / Inhaltseinheit",
        physical_unit: "Physische Einheit",
        person: "Person",
        incipit: "Incipit",
        explicit_colophon: "Explicit / Kolophon",
        addition: "Nachtrag / Vermerk",
        catalogue: "Historische Katalogbeschreibung"
    };

    function entityOrder() {
        if (manifest && Array.isArray(manifest.entityTypes) && manifest.entityTypes.length) {
            return manifest.entityTypes.map(function (entry) { return entry.id; });
        }
        return fallbackEntityOrder.slice();
    }

    function entityLabel(type) {
        if (manifest && Array.isArray(manifest.entityTypes)) {
            var found = manifest.entityTypes.find(function (entry) { return entry.id === type; });
            if (found) { return found.label; }
        }
        return fallbackEntityLabels[type] || type.replace(/_/g, " ");
    }

    function selectedFieldText(doc) {
        var fields = doc.fields || {};
        switch (fieldFilter.value) {
        case "signature":
            return fields.signature || doc.signature || "";
        case "contents":
            return fields.titles || "";
        case "persons":
            return fields.persons || "";
        case "incipit":
            return fields.incipits || "";
        case "explicit":
            return fields.explicits || "";
        case "physical":
            return fields.physical || "";
        case "german":
            return fields.german || "";
        case "latin":
            return fields.latin || "";
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
        if (entityFilter.value && doc.entityType !== entityFilter.value) {
            return false;
        }
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
            if (fields.physical.indexOf(term) !== -1) { points += 12; }
            if (fields.notes.indexOf(term) !== -1) { points += 9; }
            if (fields.german.indexOf(term) !== -1) { points += 5; }
            if (fields.latin.indexOf(term) !== -1) { points += 5; }
            if (fields.catalogue.indexOf(term) !== -1) { points += 4; }
        });
        if (fieldFilter.value !== "all") { points += 25; }
        if (entityFilter.value) { points += 15; }
        return points;
    }

    function compareResults(a, b) {
        if (a.score !== b.score) {
            return b.score - a.score;
        }
        var sig = CatalogusData.naturalCompare(a.doc.signature, b.doc.signature);
        if (sig) { return sig; }
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
                { label: "Titel / Inhalt", value: fields.titles },
                { label: "Personen", value: fields.persons },
                { label: "Incipit", value: fields.incipits },
                { label: "Explicit / Kolophon", value: fields.explicits },
                { label: "Physische Beschreibung", value: fields.physical },
                { label: "Notiz", value: fields.notes }
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

    function uniqueRecordCount(found) {
        return new Set(found.map(function (result) { return result.doc.recordId; })).size;
    }

    function statsByEntity(found) {
        var stats = {};
        found.forEach(function (result) {
            var type = result.doc.entityType || "unknown";
            if (!stats[type]) {
                stats[type] = { count: 0, recordIds: new Set() };
            }
            stats[type].count += 1;
            stats[type].recordIds.add(result.doc.recordId);
        });
        return stats;
    }

    function updateShowParam() {
        var params = new URLSearchParams(window.location.search);
        if (activeResultEntity && activeResultEntity !== "all") {
            params.set("show", activeResultEntity);
        } else {
            params.delete("show");
        }
        var query = params.toString();
        window.history.replaceState(null, "", window.location.pathname + (query ? "?" + query : ""));
    }

    function renderEntityFacets(found) {
        resultEntityFilters.replaceChildren();
        if (!found.length) {
            resultEntityFilters.hidden = true;
            return;
        }
        resultEntityFilters.hidden = false;
        var stats = statsByEntity(found);
        var intro = document.createElement("span");
        intro.className = "catalogus-facet-label";
        intro.textContent = "Ergebnisse anzeigen:";
        resultEntityFilters.appendChild(intro);

        function addButton(type, label, count, recordCount) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "catalogus-entity-chip";
            if (activeResultEntity === type) { button.classList.add("is-active"); }
            button.setAttribute("aria-pressed", activeResultEntity === type ? "true" : "false");
            button.dataset.entityView = type;
            var main = document.createElement("span");
            main.textContent = label + " (" + count + ")";
            button.appendChild(main);
            var sub = document.createElement("small");
            sub.textContent = recordCount + (recordCount === 1 ? " Codex" : " Codices");
            button.appendChild(sub);
            button.addEventListener("click", function () {
                activeResultEntity = type;
                updateShowParam();
                renderResults(lastFound, lastRawQuery, true);
            });
            resultEntityFilters.appendChild(button);
        }

        addButton("all", "Alle", found.length, uniqueRecordCount(found));
        entityOrder().forEach(function (type) {
            if (!stats[type]) { return; }
            addButton(type, entityLabel(type), stats[type].count, stats[type].recordIds.size);
        });
    }

    function cardTitle(doc) {
        if (doc.entityType === "codex" || doc.entityType === "catalogue") {
            return doc.signature + " — " + doc.title;
        }
        return doc.title || doc.signature;
    }

    function buttonLabel(doc) {
        switch (doc.entityType) {
        case "codex": return "Zur Handschrift";
        case "content": return "Zur Inhaltseinheit";
        case "physical_unit": return "Zur physischen Einheit";
        case "person": return "Zur Personenangabe";
        case "incipit": return "Zum Incipit";
        case "explicit_colophon": return "Zum Explicit / Kolophon";
        case "addition": return "Zum Vermerk";
        case "catalogue": return "Zur Katalogbeschreibung";
        default: return "Zum Treffer";
        }
    }

    function renderCard(result, hasQuery) {
        var doc = result.doc;
        var article = document.createElement("article");
        article.className = "catalogus-result-card";

        var source = document.createElement("p");
        source.className = "catalogus-result-source";
        var entityBadge = document.createElement("span");
        entityBadge.className = "catalogus-badge catalogus-badge-entity";
        entityBadge.textContent = doc.entityLabel || entityLabel(doc.entityType);
        source.appendChild(entityBadge);
        if (doc.sourceLabel && doc.sourceLabel !== doc.entityLabel) {
            var sourceBadge = document.createElement("span");
            sourceBadge.className = "catalogus-badge";
            sourceBadge.textContent = doc.sourceLabel;
            source.appendChild(sourceBadge);
        }
        article.appendChild(source);

        var heading = document.createElement("h4");
        var link = document.createElement("a");
        link.href = detailHref(doc);
        CatalogusData.appendHighlightedText(link, cardTitle(doc), result.terms);
        heading.appendChild(link);
        article.appendChild(heading);

        if (doc.parentTitle && doc.entityType !== "content") {
            var parent = document.createElement("p");
            parent.className = "catalogus-result-context";
            parent.textContent = "Kontext: " + doc.parentTitle;
            article.appendChild(parent);
        }

        var meta = document.createElement("p");
        meta.className = "catalogus-result-meta";
        var metaParts = [];
        if (doc.entityType !== "codex" && doc.entityType !== "catalogue") { metaParts.push(doc.signature); }
        if (doc.roleDisplay) { metaParts.push(doc.roleDisplay); }
        if (doc.physicalUnit) { metaParts.push(doc.physicalUnit); }
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
        button.textContent = buttonLabel(doc);
        article.appendChild(button);
        return article;
    }

    function renderGroup(type, group, hasQuery, isSingleView) {
        var section = document.createElement("section");
        section.className = "catalogus-result-group";
        var heading = document.createElement("h3");
        heading.textContent = entityLabel(type) + " (" + group.length + ")";
        section.appendChild(heading);
        var summary = document.createElement("p");
        summary.className = "catalogus-result-group-meta";
        var records = uniqueRecordCount(group);
        summary.textContent = records + (records === 1 ? " Codex mit Treffern" : " Codices mit Treffern");
        section.appendChild(summary);

        var list = document.createElement("div");
        list.className = "catalogus-result-group-list";
        var limit = isSingleView ? 100 : 25;
        group.slice(0, limit).forEach(function (result) {
            list.appendChild(renderCard(result, hasQuery));
        });
        section.appendChild(list);
        if (group.length > limit) {
            var note = document.createElement("p");
            note.className = "catalogus-pagination-note";
            if (isSingleView) {
                note.textContent = "Die ersten 100 Treffer dieses Entitätstyps werden angezeigt. Bitte Suche oder Filter weiter eingrenzen.";
            } else {
                note.textContent = "Es werden zunächst " + limit + " von " + group.length + " Treffern gezeigt. Wählen Sie oben diesen Entitätstyp aus, um mehr Treffer anzuzeigen.";
            }
            section.appendChild(note);
        }
        return section;
    }

    function renderResults(found, rawQuery, keepFacets) {
        lastFound = found;
        lastRawQuery = rawQuery;
        results.replaceChildren();
        var hasQuery = rawQuery.trim().length > 0;
        var hasFilters = Boolean(
            dateFrom.value || dateTo.value || repositoryFilter.value || entityFilter.value || fieldFilter.value !== "all"
        );
        if (!hasQuery && !hasFilters) {
            resultEntityFilters.hidden = true;
            status.textContent = manifest.recordCount + " Handschriften und " + manifest.itemCount + " strukturierte Inhaltseinheiten sind geladen. Bitte Suchbegriff eingeben oder Filter setzen.";
            return;
        }

        var recordCount = uniqueRecordCount(found);
        status.textContent = found.length + " Treffer in " + recordCount + (recordCount === 1 ? " Codex." : " Codices.");
        if (!keepFacets) { renderEntityFacets(found); }
        else { renderEntityFacets(found); }

        if (!found.length) {
            var empty = document.createElement("p");
            empty.className = "catalogus-search-empty";
            empty.textContent = "Keine Treffer gefunden. Bei gesetztem Datumsfilter werden nur Handschriften mit numerisch normalisierter Entstehungsdatierung berücksichtigt.";
            results.appendChild(empty);
            return;
        }

        var visible = activeResultEntity === "all" ? found : found.filter(function (result) {
            return result.doc.entityType === activeResultEntity;
        });
        if (!visible.length && activeResultEntity !== "all") {
            activeResultEntity = "all";
            updateShowParam();
            renderEntityFacets(found);
            visible = found;
        }

        var grouped = {};
        visible.forEach(function (result) {
            var type = result.doc.entityType || "unknown";
            if (!grouped[type]) { grouped[type] = []; }
            grouped[type].push(result);
        });
        var order = entityOrder();
        Object.keys(grouped).forEach(function (type) {
            if (order.indexOf(type) === -1) { order.push(type); }
        });
        var singleView = activeResultEntity !== "all";
        order.forEach(function (type) {
            if (!grouped[type] || !grouped[type].length) { return; }
            results.appendChild(renderGroup(type, grouped[type], hasQuery, singleView));
        });
    }

    function runSearch() {
        renderResults(search(queryInput.value), queryInput.value, false);
    }

    function populateRepositories() {
        Object.keys(manifest.repositories || {}).sort(CatalogusData.naturalCompare).forEach(function (name) {
            var option = document.createElement("option");
            option.value = name;
            option.textContent = name + " (" + manifest.repositories[name] + ")";
            repositoryFilter.appendChild(option);
        });
    }

    function populateEntityTypes() {
        var types = Array.isArray(manifest.entityTypes) ? manifest.entityTypes : [];
        types.forEach(function (entry) {
            var option = document.createElement("option");
            option.value = entry.id;
            option.textContent = entry.label + " (" + entry.count + ")";
            entityFilter.appendChild(option);
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
                    physical: CatalogusData.searchable(fields.physical || ""),
                    german: CatalogusData.searchable(fields.german || ""),
                    latin: CatalogusData.searchable(fields.latin || ""),
                    catalogue: CatalogusData.searchable(fields.catalogue || "")
                }
            };
        });
        populateRepositories();
        populateEntityTypes();
        status.textContent = manifest.recordCount + " Handschriften und " + manifest.itemCount + " strukturierte Inhaltseinheiten sind geladen. Bitte Suchbegriff eingeben oder Filter setzen.";

        var params = new URLSearchParams(window.location.search);
        if (params.get("q")) { queryInput.value = params.get("q"); }
        if (params.get("field")) { fieldFilter.value = params.get("field"); }
        if (params.get("entity")) { entityFilter.value = params.get("entity"); }
        if (params.get("from")) { dateFrom.value = params.get("from"); }
        if (params.get("to")) { dateTo.value = params.get("to"); }
        if (params.get("repository")) { repositoryFilter.value = params.get("repository"); }
        if (params.get("show")) { activeResultEntity = params.get("show"); }
        if (queryInput.value || dateFrom.value || dateTo.value || repositoryFilter.value || entityFilter.value || fieldFilter.value !== "all") {
            runSearch();
        }
    }

    function updateUrlAndSearch(event) {
        if (event) { event.preventDefault(); }
        var params = new URLSearchParams();
        if (queryInput.value.trim()) { params.set("q", queryInput.value.trim()); }
        if (fieldFilter.value !== "all") { params.set("field", fieldFilter.value); }
        if (entityFilter.value) { params.set("entity", entityFilter.value); }
        if (dateFrom.value) { params.set("from", dateFrom.value); }
        if (dateTo.value) { params.set("to", dateTo.value); }
        if (repositoryFilter.value) { params.set("repository", repositoryFilter.value); }
        if (activeResultEntity !== "all") { params.set("show", activeResultEntity); }
        var query = params.toString();
        window.history.replaceState(null, "", window.location.pathname + (query ? "?" + query : ""));
        runSearch();
    }

    form.addEventListener("submit", updateUrlAndSearch);
    fieldFilter.addEventListener("change", updateUrlAndSearch);
    entityFilter.addEventListener("change", function (event) {
        activeResultEntity = "all";
        updateUrlAndSearch(event);
    });
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
