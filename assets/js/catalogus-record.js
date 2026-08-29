(function () {
    "use strict";

    var root = document.querySelector("[data-catalogus-record]");
    if (!root || !window.CatalogusData) {
        return;
    }

    var status = root.querySelector("[data-record-status]");
    var content = root.querySelector("[data-record-content]");
    var recordUrl = root.getAttribute("data-record-url");
    var baseUrl = document.querySelector('link[rel="stylesheet"][href*="/style.css"]');
    var inferredBase = "";
    if (baseUrl) {
        inferredBase = baseUrl.getAttribute("href").replace(/\/style\.css(?:\?.*)?$/, "");
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) { node.className = className; }
        if (text !== undefined && text !== null) { node.textContent = CatalogusData.text(text); }
        return node;
    }

    function hasValue(value) {
        if (value === null || value === undefined || value === "") { return false; }
        if (Array.isArray(value)) { return value.length > 0; }
        if (typeof value === "object") { return Object.keys(value).some(function (key) { return hasValue(value[key]); }); }
        return true;
    }

    function humanValue(value) {
        if (!hasValue(value)) { return ""; }
        if (Array.isArray(value)) {
            return value.map(humanValue).filter(Boolean).join("; ");
        }
        if (typeof value === "object") {
            var preferred = ["display", "description", "text", "original", "translation", "name", "note", "event", "place", "from", "to"];
            for (var i = 0; i < preferred.length; i += 1) {
                if (hasValue(value[preferred[i]])) { return humanValue(value[preferred[i]]); }
            }
            return Object.keys(value).filter(function (key) { return hasValue(value[key]); }).map(function (key) {
                return key.replace(/_/g, " ") + ": " + humanValue(value[key]);
            }).join("; ");
        }
        return CatalogusData.text(value);
    }

    function addDefinition(dl, label, value) {
        var rendered = humanValue(value);
        if (!rendered) { return; }
        dl.appendChild(el("dt", "", label));
        dl.appendChild(el("dd", "", rendered));
    }

    function section(title, id) {
        var wrapper = el("section", "catalogus-section");
        if (id) { wrapper.id = id; }
        wrapper.appendChild(el("h3", "", title));
        return wrapper;
    }

    function titleBadge(typeRaw, typeLabel) {
        if (!typeRaw || typeRaw === "unspecified") { return null; }
        var badge = el("span", "catalogus-badge");
        if (typeRaw === "supplied" || typeRaw === "inferred") {
            badge.classList.add("catalogus-badge-supplied");
        }
        badge.textContent = typeLabel || typeRaw.replace(/_/g, " ");
        return badge;
    }

    function renderPersons(persons, heading, id) {
        if (!Array.isArray(persons) || !persons.length) { return null; }
        var wrapper = heading ? section(heading, id) : document.createDocumentFragment();
        var list = el("ul", "catalogus-person-list");
        persons.forEach(function (person) {
            var li = el("li");
            var main = el("div");
            main.appendChild(el("strong", "", person.name));
            if (person.roleLabel) {
                main.appendChild(document.createTextNode(" — "));
                main.appendChild(el("span", "catalogus-person-role", person.roleLabel));
            }
            li.appendChild(main);
            var scopeLabel = "";
            if (person.scope === "item" && person.itemId) { scopeLabel = "Inhaltseinheit " + person.itemId.replace(/^item-/, ""); }
            else if (person.scope === "contents") { scopeLabel = "Inhaltsbeschreibung"; }
            var details = [scopeLabel, person.affiliation, person.certainty, person.note].filter(Boolean).join(" · ");
            if (details) { li.appendChild(el("div", "catalogus-result-meta", details)); }
            list.appendChild(li);
        });
        wrapper.appendChild(list);
        return wrapper;
    }

    function incipitBlock(label, data, id) {
        if (!hasValue(data)) { return null; }
        var box = el("div", "catalogus-inc-exp");
        if (id) { box.id = id; }
        var head = label;
        if (typeof data === "object" && !Array.isArray(data)) {
            if (data.label) { head += " — " + data.label; }
            if (data.locus) { head += " (" + data.locus + ")"; }
        }
        box.appendChild(el("strong", "", head + ": "));
        if (typeof data === "object" && !Array.isArray(data)) {
            var parts = [];
            if (data.text) { parts.push(data.text); }
            else if (data.original) { parts.push(data.original); }
            if (data.translation) { parts.push("Übersetzung: " + data.translation); }
            if (!parts.length) { parts.push(humanValue(data)); }
            box.appendChild(document.createTextNode(parts.join(" — ")));
        } else {
            box.appendChild(document.createTextNode(humanValue(data)));
        }
        return box;
    }

    function renderTextEntries(article, label, entries, itemId, kind) {
        if (!Array.isArray(entries) || !entries.length) { return; }
        entries.forEach(function (entry, index) {
            var box = incipitBlock(label, entry, itemId + "-" + kind + "-" + (index + 1));
            if (box) { article.appendChild(box); }
        });
    }

    function renderItem(item, depth) {
        var article = el("article", "catalogus-item");
        article.id = item.id;
        var heading = el(depth > 0 ? "h5" : "h4", "");
        if (item.label) {
            heading.appendChild(el("span", "catalogus-item-label", item.label + ")"));
            heading.appendChild(document.createTextNode(" "));
        }
        heading.appendChild(document.createTextNode(item.title && item.title.text ? item.title.text : "Inhaltseinheit"));
        var badge = item.title ? titleBadge(item.title.typeRaw, item.title.typeLabel) : null;
        if (badge) { heading.appendChild(document.createTextNode(" ")); heading.appendChild(badge); }
        article.appendChild(heading);

        var metaParts = [];
        if (item.locus) { metaParts.push(item.locus); }
        if (item.physicalUnit) { metaParts.push("Physische Einheit: " + item.physicalUnit); }
        if (item.language) { metaParts.push("Sprache: " + item.language); }
        if (item.type) { metaParts.push(item.type); }
        if (metaParts.length) { article.appendChild(el("p", "catalogus-item-meta", metaParts.join(" · "))); }

        renderTextEntries(article, "Incipit", item.incipits || (item.incipit ? [item.incipit] : []), item.id, "incipit");
        renderTextEntries(article, "Explicit", item.explicits || [], item.id, "explicit");
        renderTextEntries(article, "Kolophon", item.colophons || [], item.id, "colophon");
        if ((!item.explicits || !item.explicits.length) && (!item.colophons || !item.colophons.length) && item.explicit) {
            var legacyExp = incipitBlock("Explicit / Kolophon", item.explicit, item.id + "-explicit-1");
            if (legacyExp) { article.appendChild(legacyExp); }
        }

        if (Array.isArray(item.dates) && item.dates.length) {
            var dates = item.dates.map(function (entry) { return entry.display; }).filter(Boolean);
            if (dates.length) { article.appendChild(el("p", "catalogus-item-meta", "Datierung der Inhaltseinheit: " + dates.join(" · "))); }
        }

        if (Array.isArray(item.notes) && item.notes.length) {
            var notes = el("ul", "catalogus-note-list");
            item.notes.forEach(function (note) {
                notes.appendChild(el("li", "", note.text));
            });
            article.appendChild(notes);
        }

        var persons = renderPersons(item.persons, "");
        if (persons) { article.appendChild(persons); }

        if (Array.isArray(item.subitems) && item.subitems.length) {
            item.subitems.forEach(function (child) { article.appendChild(renderItem(child, depth + 1)); });
        }
        return article;
    }

    function renderPhysical(record) {
        var p = record.physicalDescription || {};
        if (!hasValue(p)) { return null; }
        var wrapper = section("Physische Beschreibung");
        var dl = el("dl", "catalogus-detail-grid");
        addDefinition(dl, "Objektform", p.objectForm);
        addDefinition(dl, "Material", p.support);
        addDefinition(dl, "Umfang", p.extent);
        addDefinition(dl, "Format", p.format);
        if (p.binding) {
            var binding = [];
            if (p.binding.code) { binding.push("Katalogkürzel " + p.binding.code); }
            if (p.binding.description) { binding.push(p.binding.description); }
            if (p.binding.certainty) { binding.push("Sicherheit: " + p.binding.certainty); }
            if (p.binding.note) { binding.push(p.binding.note); }
            addDefinition(dl, "Einband", binding.join(" · "));
        }
        addDefinition(dl, "Hände", p.handDescription);
        addDefinition(dl, "Zustand", p.condition);
        addDefinition(dl, "Ausstattung", p.decoration);
        addDefinition(dl, "Lagen / Kollation", p.collation);
        addDefinition(dl, "Layout", p.layout);
        wrapper.appendChild(dl);
        return wrapper;
    }

    function renderPhysicalUnits(record) {
        var units = record.physicalUnits || [];
        if (!Array.isArray(units) || !units.length) { return null; }
        var wrapper = section("Physische Einheiten");
        wrapper.appendChild(el("p", "catalogus-record-status", "Dieser Abschnitt zeigt nur physische Einheiten, die in den strukturierten Masterdaten ausdrücklich mit Inhaltseinheiten verknüpft sind."));
        units.forEach(function (unit) {
            var article = el("article", "catalogus-item");
            article.id = unit.id;
            article.appendChild(el("h4", "", unit.label || "Physische Einheit"));
            if (Array.isArray(unit.titles) && unit.titles.length) {
                var list = el("ul", "catalogus-note-list");
                unit.titles.forEach(function (title, index) {
                    var li = el("li");
                    var itemId = Array.isArray(unit.itemIds) ? unit.itemIds[index] : "";
                    if (itemId) {
                        var a = el("a", "", title);
                        a.href = "#" + itemId;
                        li.appendChild(a);
                    } else {
                        li.textContent = title;
                    }
                    list.appendChild(li);
                });
                article.appendChild(list);
            }
            wrapper.appendChild(article);
        });
        return wrapper;
    }

    function renderHistory(record) {
        var history = record.history || {};
        if (!hasValue(history)) { return null; }
        var wrapper = section("Entstehung und Geschichte");
        var dl = el("dl", "catalogus-detail-grid");
        var origin = history.origin || {};
        if (origin.date) {
            var dateText = origin.date.display || "";
            if (origin.date.qualifier) { dateText += (dateText ? " · " : "") + origin.date.qualifier; }
            if (origin.date.certainty) { dateText += (dateText ? " · " : "") + "Sicherheit: " + origin.date.certainty; }
            addDefinition(dl, "Entstehungszeit", dateText);
        }
        addDefinition(dl, "Entstehungsort", origin.place);
        addDefinition(dl, "Institution / Kontext", origin.institution);
        addDefinition(dl, "Anmerkung zur Entstehung", origin.note);
        if (dl.children.length) { wrapper.appendChild(dl); }

        if (Array.isArray(history.provenance) && history.provenance.length) {
            wrapper.appendChild(el("h4", "", "Provenienz"));
            var prov = el("ul", "catalogus-note-list");
            history.provenance.forEach(function (entry) { prov.appendChild(el("li", "", humanValue(entry))); });
            wrapper.appendChild(prov);
        }
        if (Array.isArray(history.notes) && history.notes.length) {
            var notes = el("ul", "catalogus-note-list");
            history.notes.forEach(function (entry) { notes.appendChild(el("li", "", humanValue(entry.value))); });
            wrapper.appendChild(notes);
        }
        return wrapper;
    }

    function renderRelations(record) {
        if (!Array.isArray(record.relations) || !record.relations.length) { return null; }
        var wrapper = section("Verwandte Handschriften");
        var list = el("ul", "catalogus-relation-list");
        record.relations.forEach(function (relation) {
            var li = el("li");
            li.appendChild(el("span", "catalogus-person-role", relation.typeLabel + ": "));
            if (relation.targetId) {
                var link = el("a", "", relation.targetSignature || relation.targetRaw);
                link.href = inferredBase + "/bibliothek/catalogus-codicum/handschriften/" + relation.targetId + "/";
                li.appendChild(link);
            } else {
                li.appendChild(document.createTextNode(relation.targetSignature || relation.targetRaw));
            }
            var details = [];
            if (relation.appliesTo && relation.appliesTo.length) { details.push("betrifft: " + relation.appliesTo.join(", ")); }
            if (relation.certainty) { details.push("Sicherheit: " + relation.certainty); }
            if (relation.note) { details.push(relation.note); }
            if (details.length) { li.appendChild(el("div", "catalogus-result-meta", details.join(" · "))); }
            list.appendChild(li);
        });
        wrapper.appendChild(list);
        return wrapper;
    }

    function renderNotes(record) {
        var additions = record.additions || [];
        var editorial = record.editorialNotes || [];
        if (!additions.length && !editorial.length) { return null; }
        var wrapper = section("Weitere Vermerke und redaktionelle Hinweise", "additions");
        if (additions.length) {
            wrapper.appendChild(el("h4", "", "Historische Vermerke / Ergänzungen"));
            var additionsList = el("ul", "catalogus-note-list");
            additions.forEach(function (entry, index) {
                var li = el("li", "", humanValue(entry));
                li.id = "addition-" + (index + 1);
                additionsList.appendChild(li);
            });
            wrapper.appendChild(additionsList);
        }
        if (editorial.length) {
            wrapper.appendChild(el("h4", "", "Redaktionelle Hinweise"));
            var editorialList = el("ul", "catalogus-note-list");
            editorial.forEach(function (entry) { editorialList.appendChild(el("li", "", humanValue(entry))); });
            wrapper.appendChild(editorialList);
        }
        return wrapper;
    }

    function renderCatalogue(record, language) {
        var isGerman = language === "de";
        var wrapper = section(isGerman ? "Deutsche Übersetzung" : "Lateinischer Originaltext", "catalogue-" + language);
        var block = el("div", "catalogus-catalogue-text");
        block.innerHTML = isGerman ? record.catalogue.germanHtml : record.catalogue.latinHtml;
        wrapper.appendChild(block);
        return wrapper;
    }

    function render(record) {
        status.remove();
        content.replaceChildren();

        var card = el("section", "catalogus-record-card");
        card.appendChild(el("p", "catalogus-record-kicker", "Katalog der frühneuzeitlichen Handschriften · strukturierte Erschließung"));
        card.appendChild(el("p", "catalogus-record-signature", record.signature));
        var title = el("h2", "catalogus-record-title", record.heading.title);
        var badge = titleBadge(record.heading.titleTypeRaw, record.heading.titleTypeLabel);
        if (badge) { title.appendChild(document.createTextNode(" ")); title.appendChild(badge); }
        card.appendChild(title);
        if (record.heading.date) { card.appendChild(el("p", "catalogus-record-date", record.heading.date)); }
        var overview = el("dl", "catalogus-overview-grid");
        addDefinition(overview, "Signatur", record.signature);
        addDefinition(overview, "Aufbewahrung", record.repository);
        addDefinition(overview, "Katalogseite", record.catalogPage);
        addDefinition(overview, "Alte / alternative Signaturen", record.aliases);
        if (record.history && record.history.origin) {
            addDefinition(overview, "Entstehungsort", record.history.origin.place);
        }
        if (record.physicalDescription) {
            addDefinition(overview, "Material", record.physicalDescription.support);
            addDefinition(overview, "Umfang", record.physicalDescription.extent);
            addDefinition(overview, "Format", record.physicalDescription.format);
        }
        card.appendChild(overview);
        var sourceActions = el("div", "catalogus-source-actions");
        var sourceLink = el("a", "button-link-secondary", "Historisches Digitalisat auf Archive.org");
        sourceLink.href = "https://archive.org/details/seitenstetten-catalogus-codicum";
        sourceLink.target = "_blank";
        sourceLink.rel = "noopener";
        sourceActions.appendChild(sourceLink);
        card.appendChild(sourceActions);
        content.appendChild(card);

        var note = el("div", "catalogus-intro-note");
        note.textContent = "Die digitale Erschließung des Catalogus Codicum wird laufend weiterentwickelt. Die historischen Katalogtexte und Übersetzungen sind vollständig verfügbar; die strukturierten Metadaten werden in weiteren fachlichen Redaktionsschritten normalisiert und ergänzt.";
        content.appendChild(note);

        if ((record.contentsOverview && hasValue(record.contentsOverview)) || (Array.isArray(record.contents) && record.contents.length)) {
            var contents = section("Inhalt");
            var overviewData = record.contentsOverview || {};
            if (overviewData.translation) {
                contents.appendChild(el("p", "catalogus-result-context", "Übersetzung / Inhaltscharakterisierung: " + overviewData.translation));
            }
            if (overviewData.summary) { contents.appendChild(el("p", "", overviewData.summary)); }
            var overviewMeta = [];
            if (overviewData.locus) { overviewMeta.push(overviewData.locus); }
            if (overviewData.language) { overviewMeta.push("Sprache: " + overviewData.language); }
            if (overviewData.part) { overviewMeta.push("Teil: " + overviewData.part); }
            if (overviewData.completeness) { overviewMeta.push("Erhaltungs-/Vollständigkeitsangabe: " + overviewData.completeness); }
            if (overviewMeta.length) { contents.appendChild(el("p", "catalogus-item-meta", overviewMeta.join(" · "))); }
            renderTextEntries(contents, "Incipit", overviewData.incipits || (overviewData.incipit ? [overviewData.incipit] : []), "contents-overview", "incipit");
            renderTextEntries(contents, "Explicit", overviewData.explicits || [], "contents-overview", "explicit");
            renderTextEntries(contents, "Kolophon", overviewData.colophons || [], "contents-overview", "colophon");
            if ((!overviewData.explicits || !overviewData.explicits.length) && (!overviewData.colophons || !overviewData.colophons.length) && overviewData.explicit) {
                var overviewExp = incipitBlock("Explicit / Kolophon", overviewData.explicit, "contents-overview-explicit-1");
                if (overviewExp) { contents.appendChild(overviewExp); }
            }
            if (overviewData.note) { contents.appendChild(el("p", "", overviewData.note)); }
            (record.contents || []).forEach(function (item) { contents.appendChild(renderItem(item, 0)); });
            content.appendChild(contents);
        }

        var persons = renderPersons(record.persons, "Personen", "persons");
        if (persons) { content.appendChild(persons); }
        var physical = renderPhysical(record);
        if (physical) { content.appendChild(physical); }
        var physicalUnits = renderPhysicalUnits(record);
        if (physicalUnits) { content.appendChild(physicalUnits); }
        var history = renderHistory(record);
        if (history) { content.appendChild(history); }
        var relations = renderRelations(record);
        if (relations) { content.appendChild(relations); }
        var notes = renderNotes(record);
        if (notes) { content.appendChild(notes); }

        var historical = section("Historische Katalogbeschreibung");
        historical.appendChild(el("p", "catalogus-record-status", "Die folgenden beiden Abschnitte geben die historische Quellenebene wieder: zuerst die deutsche Übersetzung, anschließend den lateinischen Originaltext."));
        content.appendChild(historical);
        content.appendChild(renderCatalogue(record, "de"));
        content.appendChild(renderCatalogue(record, "la"));

        if (window.location.hash) {
            window.setTimeout(function () {
                var target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
                if (target) { target.scrollIntoView({ block: "start" }); }
            }, 0);
        }
    }

    CatalogusData.loadJson(recordUrl, "Handschriftenbeschreibung konnte nicht geladen werden.")
        .then(render)
        .catch(function (error) {
            status.textContent = error.message;
            status.classList.add("catalogus-loading-error");
        });
}());
