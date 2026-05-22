// static/js/altas.js

// Array para almacenar los IDs de solicitudes seleccionadas
let selectedSolicitudes = [];

// Cargar selecciones guardadas al cargar la página
document.addEventListener("DOMContentLoaded", function() {
    loadSelectedSolicitudes();
    updateSelectAllButtons();
});

// Función para guardar selecciones en localStorage
function saveSelectedSolicitudes() {
    localStorage.setItem('selectedSolicitudes', JSON.stringify(selectedSolicitudes));
}

// Función para cargar selecciones desde localStorage
function loadSelectedSolicitudes() {
    const saved = localStorage.getItem('selectedSolicitudes');
    if (saved) {
        selectedSolicitudes = JSON.parse(saved);
        // Marcar los checkboxes correspondientes
        selectedSolicitudes.forEach(solicitudId => {
            const checkbox = document.querySelector(`input[name="solicitudes"][value="${solicitudId}"]`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }
}

// Manejador de cambio en checkboxes
function handleCheckboxChange(checkbox) {
    const solicitudId = checkbox.value;
    
    if (checkbox.checked) {
        // Añadir a selecciones si no está
        if (!selectedSolicitudes.includes(solicitudId)) {
            selectedSolicitudes.push(solicitudId);
        }
    } else {
        // Eliminar de selecciones si estaba
        const index = selectedSolicitudes.indexOf(solicitudId);
        if (index !== -1) {
            selectedSolicitudes.splice(index, 1);
        }
    }
    
    // Guardar en localStorage
    saveSelectedSolicitudes();
    updateSelectAllButtons();
}

// Función para actualizar el estado de los botones de selección
function updateSelectAllButtons() {
    const checkboxes = document.querySelectorAll('input[name="solicitudes"]');
    const allCheckboxes = Array.from(checkboxes);
    
    if (allCheckboxes.length === 0) return;
    
    const checkedCount = allCheckboxes.filter(cb => cb.checked).length;
    const selectAllBtn = document.querySelector('button[onclick^="selectAll"]');
    
    // Actualizar el texto del botón de "Seleccionar todo" según el estado
    if (selectAllBtn) {
        if (checkedCount === 0) {
            selectAllBtn.textContent = 'Seleccionar todo';
        } else if (checkedCount < allCheckboxes.length) {
            selectAllBtn.textContent = 'Seleccionar todo (parcial)';
        } else {
            selectAllBtn.textContent = 'Seleccionar todo (todos)';
        }
    }
}

// Función personalizada para seleccionar/deseleccionar todo
function selectAllSolicitudes(bool) {
    const checkboxes = document.querySelectorAll('input[name="solicitudes"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = bool;
        // Actualizar la lista de selección
        handleCheckboxChange(checkbox);
    });
    updateSelectAllButtons();
}

// Manejar eventos de cambio en checkboxes
document.addEventListener('change', function(e) {
    if (e.target.name === 'solicitudes') {
        handleCheckboxChange(e.target);
    }
});

// Limpiar selecciones cuando se carga una nueva página (HTMX)
document.addEventListener("htmx:beforeRequest", function(evt) {
    // Si se va a hacer una llamada HTMX, guardamos las selecciones
    if (evt.detail.elt.id === 'solicitudes-container') {
        saveSelectedSolicitudes();
    }
});

// Evento después de que se actualiza el contenido de la página
document.addEventListener("htmx:afterSwap", function(evt) {
    // Recargar selecciones después de cada actualización HTMX
    loadSelectedSolicitudes();
    updateSelectAllButtons();
});