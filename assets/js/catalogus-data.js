(function () {
    "use strict";

    function text(value) {
        return value === null || value === undefined ? "" : String(value);
    }

    function germanExpanded(value) {
        return text(value)
            .replace(/ä/g, "ae")
            .replace(/ö/g, "oe")
            .replace(/ü/g, "ue")
            .replace(/Ä/g, "Ae")
            .replace(/Ö/g, "Oe")
            .replace(/Ü/g, "Ue");
    }

    function normalize(value) {
        return text(value)
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/ß/g, "ss")
            .replace(/æ/g, "ae")
            .replace(/œ/g, "oe")
            .toLocaleLowerCase("de")
            .replace(/[^\p{L}\p{N}_]+/gu, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function searchable(value) {
        return (normalize(value) + " " + normalize(germanExpanded(value))).trim();
    }

    function queryTerms(value) {
        return Array.from(new Set(searchable(value).split(/\s+/).filter(function (term) {
            return term.length >= 2;
        })));
    }

    function naturalCompare(a, b) {
        return text(a).localeCompare(text(b), "de", { numeric: true, sensitivity: "base" });
    }

    function loadJson(url, message) {
        return fetch(url).then(function (response) {
            if (!response.ok) {
                throw new Error(message || "Daten konnten nicht geladen werden.");
            }
            return response.json();
        });
    }

    function appendHighlightedText(parent, value, terms) {
        var original = text(value);
        if (!original || !terms || !terms.length) {
            parent.textContent = original;
            return;
        }
        var lower = original.toLocaleLowerCase("de");
        var ranges = [];
        terms.forEach(function (term) {
            var needle = term.toLocaleLowerCase("de");
            var index = lower.indexOf(needle);
            while (index !== -1) {
                ranges.push([index, index + needle.length]);
                index = lower.indexOf(needle, index + needle.length);
            }
        });
        if (!ranges.length) {
            parent.textContent = original;
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
                parent.appendChild(document.createTextNode(original.slice(cursor, range[0])));
            }
            var mark = document.createElement("mark");
            mark.textContent = original.slice(range[0], range[1]);
            parent.appendChild(mark);
            cursor = range[1];
        });
        if (cursor < original.length) {
            parent.appendChild(document.createTextNode(original.slice(cursor)));
        }
    }

    window.CatalogusData = {
        appendHighlightedText: appendHighlightedText,
        loadJson: loadJson,
        naturalCompare: naturalCompare,
        normalize: normalize,
        queryTerms: queryTerms,
        searchable: searchable,
        text: text
    };
}());
