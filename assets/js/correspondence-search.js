(function () {
    "use strict";

    var root = document.querySelector("[data-correspondence-search]");
    if (!root) {
        return;
    }

    var form = root.querySelector("[data-correspondence-form]");
    var resetButton = root.querySelector("[data-correspondence-reset]");
    var status = root.querySelector("[data-correspondence-status]");
    var results = root.querySelector("[data-correspondence-results]");
    var fields = {
        sender: root.querySelector("[data-field='sender']"),
        recipient: root.querySelector("[data-field='recipient']"),
        from: root.querySelector("[data-field='from']"),
        to: root.querySelector("[data-field='to']"),
        text: root.querySelector("[data-field='text']"),
        place: root.querySelector("[data-field='place']"),
        category: root.querySelector("[data-field='category']")
    };
    var dataUrl = root.getAttribute("data-data-url");
    var treeUrl = root.getAttribute("data-tree-url");
    var records = [];
    var indexed = [];

    function text(value) {
        return String(value || "");
    }

    function stripDiacritics(value) {
        return value
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLocaleLowerCase("de");
    }

    function expandGerman(value) {
        return value
            .replace(/Ä/g, "Ae")
            .replace(/Ö/g, "Oe")
            .replace(/Ü/g, "Ue")
            .replace(/ä/g, "ae")
            .replace(/ö/g, "oe")
            .replace(/ü/g, "ue")
            .replace(/ß/g, "ss");
    }

    function normalize(value) {
        var raw = text(value);
        return stripDiacritics(raw) + " " + stripDiacritics(expandGerman(raw));
    }

    function terms(value) {
        return Array.from(new Set(normalize(value).split(/\s+/).filter(function (term) {
            return term.length >= 2;
        })));
    }

    function parseQueryDate(value, isEnd) {
        var cleaned = text(value).trim();
        var match;
        if (!cleaned) {
            return "";
        }
        match = cleaned.match(/^(\d{4})$/);
        if (match) {
            return match[1] + (isEnd ? "-12-31" : "-01-01");
        }
        match = cleaned.match(/^(\d{4})[-.\/](\d{1,2})$/);
        if (match) {
            var month = String(Number(match[2])).padStart(2, "0");
            var endDay = new Date(Number(match[1]), Number(month), 0).getDate();
            return match[1] + "-" + month + "-" + (isEnd ? String(endDay).padStart(2, "0") : "01");
        }
        match = cleaned.match(/^(\d{4})[-.\/](\d{1,2})[-.\/](\d{1,2})$/);
        if (match) {
            return match[1] + "-" + String(Number(match[2])).padStart(2, "0") + "-" + String(Number(match[3])).padStart(2, "0");
        }
        match = cleaned.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
        if (match) {
            return match[3] + "-" + String(Number(match[2])).padStart(2, "0") + "-" + String(Number(match[1])).padStart(2, "0");
        }
        return "";
    }

    function containsAll(haystack, needle) {
        var hay = normalize(haystack);
        return terms(needle).every(function (term) {
            return hay.indexOf(term) !== -1;
        });
    }

    function currentCriteria() {
        return {
            sender: fields.sender.value.trim(),
            recipient: fields.recipient.value.trim(),
            from: fields.from.value.trim(),
            to: fields.to.value.trim(),
            text: fields.text.value.trim(),
            place: fields.place.value.trim(),
            category: fields.category.value
        };
    }

    function hasCriteria(criteria) {
        return Object.keys(criteria).some(function (key) {
            return Boolean(criteria[key]);
        });
    }

    function overlaps(record, criteria) {
        var queryFrom = parseQueryDate(criteria.from, false);
        var queryTo = parseQueryDate(criteria.to, true);
        if (!queryFrom && !queryTo) {
            return true;
        }
        if (!record.dateFrom || !record.dateTo) {
            return false;
        }
        return record.dateTo >= (queryFrom || "0000-01-01") && record.dateFrom <= (queryTo || "9999-12-31");
    }

    function matches(entry, criteria) {
        var record = entry.record;
        return (!criteria.sender || containsAll(record.sender, criteria.sender))
            && (!criteria.recipient || containsAll(record.recipient, criteria.recipient))
            && (!criteria.text || containsAll(entry.fullText, criteria.text))
            && (!criteria.place || containsAll(record.place, criteria.place))
            && (!criteria.category || record.category === criteria.category)
            && overlaps(record, criteria);
    }

    function sortRecords(a, b) {
        return (a.record.dateSort || "9999-12-31").localeCompare(b.record.dateSort || "9999-12-31")
            || text(a.record.sender).localeCompare(text(b.record.sender), "de", { sensitivity: "base" })
            || text(a.record.recipient).localeCompare(text(b.record.recipient), "de", { sensitivity: "base" })
            || text(a.record.signature).localeCompare(text(b.record.signature), "de", { numeric: true, sensitivity: "base" });
    }

    function setParams(criteria) {
        var params = new URLSearchParams();
        Object.keys(criteria).forEach(function (key) {
            if (criteria[key]) {
                params.set(key, criteria[key]);
            }
        });
        var next = params.toString() ? "?" + params.toString() : window.location.pathname;
        history.replaceState(null, "", next);
    }

    function applyParams() {
        var params = new URLSearchParams(window.location.search);
        Object.keys(fields).forEach(function (key) {
            if (params.has(key)) {
                fields[key].value = params.get(key);
            }
        });
    }

    function line(label, value) {
        if (!value) {
            return null;
        }
        var paragraph = document.createElement("p");
        paragraph.className = "correspondence-line";
        var strong = document.createElement("strong");
        strong.textContent = label + ": ";
        paragraph.appendChild(strong);
        paragraph.appendChild(document.createTextNode(value));
        return paragraph;
    }

    function title(record) {
        if (record.sender && record.recipient) {
            return record.sender + " → " + record.recipient;
        }
        return record.sender || record.recipient || record.category || record.signature || "Korrespondenzstück";
    }

    function renderList(matches, criteria) {
        results.replaceChildren();
        if (!hasCriteria(criteria)) {
            status.textContent = records.length + " Datensätze verfügbar. Bitte Suchkriterien eingeben.";
            return;
        }
        status.textContent = matches.length + (matches.length === 1 ? " Treffer" : " Treffer");
        if (!matches.length) {
            var empty = document.createElement("p");
            empty.className = "archive-search-empty";
            empty.textContent = "Keine Treffer für die gewählten Suchkriterien.";
            results.appendChild(empty);
            return;
        }

        matches.slice(0, 100).forEach(function (entry) {
            var record = entry.record;
            var article = document.createElement("article");
            article.className = "correspondence-result-card";
            var heading = document.createElement("h3");
            heading.textContent = title(record);
            var meta = document.createElement("p");
            meta.className = "result-meta";
            meta.textContent = [record.category, record.dateDisplay, record.place].filter(Boolean).join(" · ");
            article.append(heading, meta);
            [line("Signatur", record.signature), line("Regest", record.regest), line("Bemerkungen", record.remarks), line("Olim", record.olim)].filter(Boolean).forEach(function (node) {
                article.appendChild(node);
            });
            if (record.archiveMatch && record.archiveId) {
                var link = document.createElement("a");
                link.className = "button-link correspondence-tree-link";
                link.href = treeUrl + "#" + encodeURIComponent(record.archiveId);
                link.textContent = "Im Archivbaum anzeigen";
                article.appendChild(link);
            }
            results.appendChild(article);
        });
        if (matches.length > 100) {
            var note = document.createElement("p");
            note.className = "search-meta";
            note.textContent = "Die ersten 100 Treffer werden angezeigt. Bitte Suchkriterien verfeinern.";
            results.appendChild(note);
        }
    }

    function runSearch() {
        var criteria = currentCriteria();
        var matchesList = indexed.filter(function (entry) {
            return matches(entry, criteria);
        }).sort(sortRecords);
        setParams(criteria);
        renderList(matchesList, criteria);
    }

    function resetSearch() {
        Object.keys(fields).forEach(function (key) {
            fields[key].value = "";
        });
        history.replaceState(null, "", window.location.pathname);
        renderList([], currentCriteria());
    }

    function fillCategories(categories) {
        categories.forEach(function (category) {
            var option = document.createElement("option");
            option.value = category;
            option.textContent = category;
            fields.category.appendChild(option);
        });
    }

    fetch(dataUrl)
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Korrespondenzdaten konnten nicht geladen werden.");
            }
            return response.json();
        })
        .then(function (payload) {
            records = payload.records || [];
            indexed = records.map(function (record) {
                return {
                    record: record,
                    fullText: [record.searchText, record.sender, record.recipient, record.place, record.category, record.signature, record.olim].join(" ")
                };
            });
            fillCategories((payload.facets && payload.facets.categories) || []);
            applyParams();
            runSearch();
        })
        .catch(function (error) {
            status.textContent = error.message;
        });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        runSearch();
    });
    resetButton.addEventListener("click", resetSearch);
}());
