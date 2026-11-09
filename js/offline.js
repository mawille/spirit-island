// Offline-Ersatz für die Wiki-Skripte: Reiter (HeaderTabs) und sortierbare Tabellen.
(function () {
    function own(layout, selector) {
        return Array.prototype.filter.call(layout.querySelectorAll(selector), function (el) {
            return el.closest('.oo-ui-indexLayout') === layout;
        });
    }

    var layouts = Array.prototype.slice.call(document.querySelectorAll('.oo-ui-indexLayout'));
    layouts.forEach(function (layout) {
        var tabs = own(layout, '[role=tab]');
        var panels = own(layout, '[role=tabpanel]');
        function select(index, updateHash) {
            tabs.forEach(function (t, i) {
                var on = i === index;
                t.classList.toggle('oo-ui-optionWidget-selected', on);
                t.setAttribute('aria-selected', on ? 'true' : 'false');
            });
            panels.forEach(function (p, i) { p.style.display = i === index ? '' : 'none'; });
            if (updateHash && panels[index] && history.replaceState) {
                history.replaceState(null, '', '#' + panels[index].id);
            }
        }
        tabs.forEach(function (t, i) {
            t.style.cursor = 'pointer';
            t.addEventListener('click', function () { select(i, true); });
        });
        layout._select = function (id) {
            for (var i = 0; i < panels.length; i++) {
                if (panels[i].id === id) { select(i, false); return true; }
            }
            return false;
        };
        select(0, false);
    });

    function fromHash() {
        var id = decodeURIComponent(location.hash.replace(/^#/, ''));
        if (!id) { return; }
        layouts.forEach(function (l) { l._select(id); });
    }
    fromHash();
    window.addEventListener('hashchange', fromHash);

    // Sortierbare Tabellen
    Array.prototype.forEach.call(document.querySelectorAll('table.sortable'), function (table) {
        var body = table.tBodies[0];
        var head = body.rows[0];
        Array.prototype.forEach.call(head.cells, function (th, col) {
            if (th.classList.contains('unsortable')) { return; }
            th.style.cursor = 'pointer';
            th.title = 'Sortieren';
            var asc = true;
            th.addEventListener('click', function () {
                var rows = Array.prototype.slice.call(body.rows, 1);
                rows.sort(function (a, b) {
                    var ca = a.cells[col], cb = b.cells[col];
                    var va = ca.getAttribute('data-sort-value') || ca.textContent.trim();
                    var vb = cb.getAttribute('data-sort-value') || cb.textContent.trim();
                    var na = parseFloat(va), nb = parseFloat(vb);
                    var r = (!isNaN(na) && !isNaN(nb)) ? na - nb : va.localeCompare(vb);
                    return asc ? r : -r;
                });
                asc = !asc;
                rows.forEach(function (r) { body.appendChild(r); });
            });
        });
    });
})();
