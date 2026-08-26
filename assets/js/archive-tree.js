(function () {
    "use strict";

    var browser = document.querySelector("[data-archive-browser]");
    if (!browser) {
        return;
    }

    var tree = browser.querySelector("[data-tree]");
    var treePanel = browser.querySelector("[data-tree-panel]");
    var toggleButton = browser.querySelector("[data-tree-toggle]");
    var recordPanel = browser.querySelector("[data-record]");
    var status = browser.querySelector("[data-browser-status]");
    var dataUrl = browser.getAttribute("data-data-url");

    var store = null;
    var expanded = new Set();
    var selectedId = "";

    function childRecords(parentId) {
        return store.childRecords(parentId);
    }

    function pathTo(recordId) {
        return store.pathTo(recordId);
    }

    function openPath(recordId) {
        pathTo(recordId).forEach(function (record) {
            expanded.add(record.id);
        });
    }

    function buildTreeList(parentId, depth) {
        var list = document.createElement("ul");
        list.className = depth === 0 ? "archive-tree-root" : "archive-tree-children";

        childRecords(parentId).forEach(function (record) {
            var hasChildren = Boolean(record.hasChildren);
            var isExpanded = expanded.has(record.id);
            var item = document.createElement("li");
            item.className = "archive-tree-item";

            var row = document.createElement("div");
            row.className = "archive-tree-row";
            row.style.setProperty("--tree-depth", depth);
            if (record.id === selectedId) {
                row.classList.add("is-current");
            }

            if (hasChildren) {
                var expander = document.createElement("button");
                expander.type = "button";
                expander.className = "archive-tree-expander";
                expander.setAttribute("aria-label", isExpanded ? "Zweig schließen" : "Zweig öffnen");
                expander.setAttribute("aria-expanded", String(isExpanded));
                expander.textContent = isExpanded ? "▾" : "▸";
                expander.addEventListener("click", function () {
                    if (expanded.has(record.id)) {
                        expanded.delete(record.id);
                    } else {
                        expanded.add(record.id);
                    }
                    renderTree();
                });
                row.appendChild(expander);
            } else {
                var spacer = document.createElement("span");
                spacer.className = "archive-tree-spacer";
                row.appendChild(spacer);
            }

            var link = document.createElement("a");
            link.href = "#" + encodeURIComponent(record.id);
            link.className = "archive-tree-link";
            link.textContent = ArchiveData.displayTitle(record);
            if (record.level) {
                link.title = record.level;
            }
            link.addEventListener("click", function (event) {
                event.preventDefault();
                selectRecord(record.id, true);
            });
            row.appendChild(link);
            item.appendChild(row);

            if (hasChildren && isExpanded) {
                item.appendChild(buildTreeList(record.id, depth + 1));
            }

            list.appendChild(item);
        });

        return list;
    }

    function renderTree() {
        tree.replaceChildren(buildTreeList("", 0));
    }

    function fieldList(items) {
        var dl = document.createElement("dl");
        dl.className = "archive-detail-grid";
        items.forEach(function (item) {
            var dt = document.createElement("dt");
            dt.textContent = item.label;
            var dd = document.createElement("dd");
            dd.textContent = item.value;
            dl.append(dt, dd);
        });
        return dl;
    }

    function makeChildList(record) {
        var children = childRecords(record.id);
        if (!children.length) {
            return null;
        }

        var section = document.createElement("section");
        section.className = "archive-child-section";
        var heading = document.createElement("h3");
        heading.textContent = "Untergeordnete Einheiten";
        var list = document.createElement("ul");
        list.className = "record-reference-list";

        children.forEach(function (child) {
            var item = document.createElement("li");
            var button = document.createElement("button");
            button.type = "button";
            button.className = "record-reference-button";
            var title = document.createElement("strong");
            title.textContent = ArchiveData.displayTitle(child);
            var meta = document.createElement("span");
            meta.textContent = [child.level, child.date].filter(Boolean).join(" | ");
            button.append(title, meta);
            button.addEventListener("click", function () {
                selectRecord(child.id, true);
            });
            item.appendChild(button);
            list.appendChild(item);
        });

        section.append(heading, list);
        return section;
    }

    function renderRecord(record) {
        var breadcrumb = document.createElement("nav");
        breadcrumb.className = "archive-breadcrumb";
        breadcrumb.setAttribute("aria-label", "Pfad");
        pathTo(record.id).forEach(function (entry, index, entries) {
            if (index > 0) {
                var separator = document.createElement("span");
                separator.textContent = "›";
                breadcrumb.appendChild(separator);
            }
            if (index === entries.length - 1) {
                var current = document.createElement("strong");
                current.textContent = entry.title;
                breadcrumb.appendChild(current);
            } else {
                var link = document.createElement("a");
                link.href = "#" + encodeURIComponent(entry.id);
                link.textContent = entry.title;
                link.addEventListener("click", function (event) {
                    event.preventDefault();
                    selectRecord(entry.id, true);
                });
                breadcrumb.appendChild(link);
            }
        });

        var title = document.createElement("h3");
        title.textContent = record.date && !record.title.includes(record.date)
            ? record.title + " (" + record.date + ")"
            : record.title;

        var lead = [
            { label: "Signatur", value: record.signature },
            { label: "Verzeichnungsstufe", value: record.level },
            { label: "Laufzeit", value: record.date }
        ].filter(function (item) { return item.value; });

        var content = document.createDocumentFragment();
        content.append(breadcrumb, title);
        if (lead.length) {
            content.appendChild(fieldList(lead));
        }

        if (record.fields && record.fields.length) {
            content.appendChild(fieldList(record.fields));
        }

        if (record.controlled && record.controlled.length) {
            record.controlled.forEach(function (group) {
                var section = document.createElement("section");
                section.className = "archive-term-section";
                var heading = document.createElement("h3");
                heading.textContent = group.label;
                var list = document.createElement("ul");
                list.className = "archive-term-list";
                group.values.forEach(function (value) {
                    var item = document.createElement("li");
                    item.textContent = value.role ? value.label + " (" + value.role + ")" : value.label;
                    list.appendChild(item);
                });
                section.append(heading, list);
                content.appendChild(section);
            });
        }

        var childList = makeChildList(record);
        if (childList) {
            content.appendChild(childList);
        }

        recordPanel.replaceChildren(content);
    }

    function selectRecord(recordId, updateHash) {
        var record = store.recordsById.get(recordId);
        if (!record) {
            return;
        }
        selectedId = recordId;
        openPath(recordId);
        renderTree();
        renderRecord(record);
        if (updateHash) {
            history.replaceState(null, "", "#" + encodeURIComponent(recordId));
        }
        if (window.matchMedia("(max-width: 760px)").matches) {
            treePanel.classList.remove("is-open");
            toggleButton.setAttribute("aria-expanded", "false");
        }
    }

    function initialize(dataStore) {
        store = dataStore;
        var initialId = "";
        if (window.location.hash) {
            initialId = decodeURIComponent(window.location.hash.slice(1));
        }
        if (!store.recordsById.has(initialId)) {
            initialId = childRecords("")[0] ? childRecords("")[0].id : "";
        }

        status.textContent = store.payload.metadata.recordCount + " Verzeichnungseinheiten";
        renderTree();
        if (initialId) {
            selectRecord(initialId, false);
        }
    }

    toggleButton.addEventListener("click", function () {
        var isOpen = treePanel.classList.toggle("is-open");
        toggleButton.setAttribute("aria-expanded", String(isOpen));
    });

    ArchiveData.load(dataUrl)
        .then(initialize)
        .catch(function (error) {
            status.textContent = error.message;
            recordPanel.textContent = "Der Archivbaum konnte nicht geladen werden.";
        });
}());
