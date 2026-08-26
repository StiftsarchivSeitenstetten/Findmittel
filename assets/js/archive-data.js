(function () {
    "use strict";

    function text(value) {
        return String(value || "");
    }

    function normalize(value) {
        return text(value)
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/ß/g, "ss")
            .replace(/æ/g, "ae")
            .replace(/œ/g, "oe")
            .toLocaleLowerCase("de");
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

    function searchable(value) {
        return normalize(value) + " " + normalize(germanExpanded(value));
    }

    function naturalCompare(a, b) {
        return text(a.signature || a.id).localeCompare(text(b.signature || b.id), "de", {
            numeric: true,
            sensitivity: "base"
        });
    }

    function displayTitle(record) {
        if (!record) {
            return "";
        }
        return record.signature ? record.signature + " - " + record.title : record.title;
    }

    function createStore(payload) {
        var recordsById = new Map();
        var childrenByParent = new Map();

        payload.records.forEach(function (record) {
            recordsById.set(record.id, record);
            if (!childrenByParent.has(record.parent || "")) {
                childrenByParent.set(record.parent || "", []);
            }
            childrenByParent.get(record.parent || "").push(record.id);
        });

        function childRecords(parentId) {
            return (childrenByParent.get(parentId || "") || [])
                .map(function (id) { return recordsById.get(id); })
                .filter(Boolean)
                .sort(function (a, b) {
                    if (typeof a.order === "number" && typeof b.order === "number") {
                        return a.order - b.order;
                    }
                    return naturalCompare(a, b);
                });
        }

        function pathTo(recordId) {
            var path = [];
            var seen = new Set();
            var record = recordsById.get(recordId);
            while (record && !seen.has(record.id)) {
                path.unshift(record);
                seen.add(record.id);
                record = recordsById.get(record.parent);
            }
            return path;
        }

        function topBranch(recordId) {
            var path = pathTo(recordId);
            return path.length > 1 ? path[1] : null;
        }

        function isAncestor(ancestorId, descendantId) {
            var record = recordsById.get(descendantId);
            var seen = new Set();
            while (record && record.parent && !seen.has(record.id)) {
                if (record.parent === ancestorId) {
                    return true;
                }
                seen.add(record.id);
                record = recordsById.get(record.parent);
            }
            return false;
        }

        return {
            payload: payload,
            records: payload.records,
            recordsById: recordsById,
            childrenByParent: childrenByParent,
            childRecords: childRecords,
            isAncestor: isAncestor,
            pathTo: pathTo,
            topBranch: topBranch
        };
    }

    function load(url) {
        return fetch(url)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Archivdaten konnten nicht geladen werden.");
                }
                return response.json();
            })
            .then(createStore);
    }

    window.ArchiveData = {
        displayTitle: displayTitle,
        load: load,
        naturalCompare: naturalCompare,
        normalize: normalize,
        searchable: searchable,
        text: text
    };
}());
