(function () {
    "use strict";

    var root = document.querySelector("[data-archive-search]");
    if (!root) {
        return;
    }

    var form = root.querySelector("[data-search-form]");
    var queryInput = root.querySelector("[data-search-query]");
    var branchFilter = root.querySelector("[data-branch-filter]");
    var levelFilter = root.querySelector("[data-level-filter]");
    var status = root.querySelector("[data-search-status]");
    var results = root.querySelector("[data-search-results]");
    var dataUrl = root.getAttribute("data-data-url");
    var treeUrl = root.getAttribute("data-tree-url");
    var store = null;
    var indexedRecords = [];

    function unique(values) {
        return Array.from(new Set(values.filter(Boolean)));
    }

    function queryTerms(value) {
        return unique(ArchiveData.searchable(value).split(/\s+/).filter(function (term) {
            return term.length >= 2;
        }));
    }

    function visiblePath(record) {
        return store.pathTo(record.id).map(function (entry) {
            return entry.title;
        });
    }

    function fieldHaystack(record) {
        var search = record.search || {};
        return {
            signature: ArchiveData.searchable(search.signature || record.signature),
            title: ArchiveData.searchable(search.title || record.title),
            terms: ArchiveData.searchable(search.terms || ""),
            date: ArchiveData.searchable(search.date || record.date),
            description: ArchiveData.searchable(search.description || ""),
            all: ArchiveData.searchable(search.text || "")
        };
    }

    function score(record, haystack, terms, rawQuery) {
        var exactSignature = ArchiveData.normalize(record.signature) === ArchiveData.normalize(rawQuery);
        var total = exactSignature ? 1000 : 0;
        terms.forEach(function (term) {
            if (haystack.signature.indexOf(term) !== -1) {
                total += exactSignature ? 0 : 80;
            }
            if (haystack.title.indexOf(term) !== -1) {
                total += 45;
            }
            if (haystack.terms.indexOf(term) !== -1) {
                total += 30;
            }
            if (haystack.date.indexOf(term) !== -1) {
                total += 15;
            }
            if (haystack.description.indexOf(term) !== -1) {
                total += 8;
            }
        });
        return total;
    }

    function snippetSource(record, terms) {
        var candidates = [];
        (record.fields || []).forEach(function (field) {
            candidates.push({ label: field.label, value: field.value });
        });
        (record.controlled || []).forEach(function (group) {
            var value = group.values.map(function (item) {
                return item.role ? item.label + " [" + item.role + "]" : item.label;
            }).join("; ");
            candidates.push({ label: group.label, value: value });
        });
        candidates.push({ label: "Titel", value: record.title });

        for (var i = 0; i < candidates.length; i += 1) {
            var normalized = ArchiveData.searchable(candidates[i].value);
            if (terms.some(function (term) { return normalized.indexOf(term) !== -1; })) {
                return candidates[i];
            }
        }
        return null;
    }

    function makeSnippet(record, terms) {
        var source = snippetSource(record, terms);
        if (!source || !source.value) {
            return "";
        }
        var value = source.value.replace(/\s+/g, " ").trim();
        var normalized = ArchiveData.normalize(value);
        var firstIndex = terms.reduce(function (best, term) {
            var index = normalized.indexOf(term);
            if (index === -1) {
                return best;
            }
            return best === -1 ? index : Math.min(best, index);
        }, -1);
        var start = firstIndex > 70 ? firstIndex - 70 : 0;
        var end = Math.min(value.length, start + 230);
        var snippet = value.slice(start, end);
        if (start > 0) {
            snippet = "..." + snippet;
        }
        if (end < value.length) {
            snippet += "...";
        }
        return source.label + ": " + snippet;
    }

    function matchesFilters(record) {
        var branch = store.topBranch(record.id);
        if (branchFilter.value && (!branch || branch.id !== branchFilter.value)) {
            return false;
        }
        if (levelFilter.value && record.level !== levelFilter.value) {
            return false;
        }
        return true;
    }

    function search(rawQuery) {
        var terms = queryTerms(rawQuery);
        if (!terms.length) {
            return [];
        }
        return indexedRecords
            .filter(function (entry) {
                return matchesFilters(entry.record) && terms.every(function (term) {
                    return entry.haystack.all.indexOf(term) !== -1;
                });
            })
            .map(function (entry) {
                return {
                    record: entry.record,
                    score: score(entry.record, entry.haystack, terms, rawQuery),
                    snippet: makeSnippet(entry.record, terms)
                };
            })
            .sort(function (a, b) {
                if (b.score !== a.score) {
                    return b.score - a.score;
                }
                return a.record.order - b.record.order;
            });
    }

    function appendHighlightedText(parent, text, terms) {
        var value = ArchiveData.text(text);
        if (!terms.length || !value) {
            parent.textContent = value;
            return;
        }
        var normalized = ArchiveData.normalize(value);
        var ranges = [];
        terms.forEach(function (term) {
            var index = normalized.indexOf(term);
            while (index !== -1) {
                ranges.push([index, index + term.length]);
                index = normalized.indexOf(term, index + term.length);
            }
        });
        if (!ranges.length) {
            parent.textContent = value;
            return;
        }
        ranges.sort(function (a, b) { return a[0] - b[0]; });
        var merged = [];
        ranges.forEach(function (range) {
            var last = merged[merged.length - 1];
            if (last && range[0] <= last[1]) {
                last[1] = Math.max(last[1], range[1]);
            } else {
                merged.push(range);
            }
        });
        var cursor = 0;
        merged.forEach(function (range) {
            if (range[0] > cursor) {
                parent.appendChild(document.createTextNode(value.slice(cursor, range[0])));
            }
            var mark = document.createElement("mark");
            mark.textContent = value.slice(range[0], range[1]);
            parent.appendChild(mark);
            cursor = range[1];
        });
        if (cursor < value.length) {
            parent.appendChild(document.createTextNode(value.slice(cursor)));
        }
    }

    function recordMeta(record) {
        return [
            record.signature ? "Signatur: " + record.signature : "",
            record.level,
            record.date
        ].filter(Boolean).join(" | ");
    }

    function renderResults(searchResults, rawQuery) {
        var terms = queryTerms(rawQuery);
        results.replaceChildren();
        if (!rawQuery.trim()) {
            status.textContent = store.payload.metadata.recordCount + " Verzeichnungseinheiten geladen. Bitte Suchbegriff eingeben.";
            return;
        }
        status.textContent = searchResults.length + (searchResults.length === 1 ? " Treffer" : " Treffer");
        if (!searchResults.length) {
            var empty = document.createElement("p");
            empty.className = "archive-search-empty";
            empty.textContent = "Keine Treffer gefunden.";
            results.appendChild(empty);
            return;
        }

        searchResults.slice(0, 80).forEach(function (result) {
            var record = result.record;
            var article = document.createElement("article");
            article.className = "archive-result-card";

            var heading = document.createElement("h3");
            appendHighlightedText(heading, record.title, terms);
            article.appendChild(heading);

            var meta = document.createElement("p");
            meta.className = "result-meta";
            meta.textContent = recordMeta(record);
            article.appendChild(meta);

            var path = document.createElement("p");
            path.className = "archive-result-path";
            path.textContent = visiblePath(record).join(" › ");
            article.appendChild(path);

            if (result.snippet) {
                var snippet = document.createElement("p");
                snippet.className = "archive-result-snippet";
                appendHighlightedText(snippet, result.snippet, terms);
                article.appendChild(snippet);
            }

            var link = document.createElement("a");
            link.className = "button-link archive-result-link";
            link.href = treeUrl + "#" + encodeURIComponent(record.id);
            link.textContent = "Im Archivbaum anzeigen";
            article.appendChild(link);
            results.appendChild(article);
        });

        if (searchResults.length > 80) {
            var note = document.createElement("p");
            note.className = "search-meta";
            note.textContent = "Die ersten 80 Treffer werden angezeigt. Bitte Suchbegriff oder Filter verfeinern.";
            results.appendChild(note);
        }
    }

    function runSearch() {
        renderResults(search(queryInput.value), queryInput.value);
    }

    function fillFilters() {
        var rootRecord = store.childRecords("")[0];
        store.childRecords(rootRecord ? rootRecord.id : "").forEach(function (record) {
            var option = document.createElement("option");
            option.value = record.id;
            option.textContent = record.title;
            branchFilter.appendChild(option);
        });

        unique(store.records.map(function (record) { return record.level; })).sort().forEach(function (level) {
            var option = document.createElement("option");
            option.value = level;
            option.textContent = level;
            levelFilter.appendChild(option);
        });
    }

    function initialize(dataStore) {
        store = dataStore;
        indexedRecords = store.records.map(function (record) {
            return {
                record: record,
                haystack: fieldHaystack(record)
            };
        });
        fillFilters();
        status.textContent = store.payload.metadata.recordCount + " Verzeichnungseinheiten geladen. Bitte Suchbegriff eingeben.";
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        runSearch();
    });
    branchFilter.addEventListener("change", runSearch);
    levelFilter.addEventListener("change", runSearch);

    ArchiveData.load(dataUrl)
        .then(initialize)
        .catch(function (error) {
            status.textContent = error.message;
        });
}());
