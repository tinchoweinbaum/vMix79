// 1. Manejo de Pestañas (Tabs)
function cambiarTab(e, tabId) {
    // Ocultar todos los contenidos
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach(content => content.classList.remove('active'));

    // Desactivar todos los botones
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Mostrar el seleccionado
    document.getElementById(tabId).classList.add('active');
    e.currentTarget.classList.add('active');
}

// 2. Control de la Consola (Expandir/Colapsar)
function toggleConsole() {
    const wrapper = document.getElementById('console-wrapper');
    const icon = document.getElementById('toggle-icon');
    
    wrapper.classList.toggle('collapsed');
    icon.innerText = wrapper.classList.contains('collapsed') ? '▲' : '▼';
}

// 3. Envío de Comandos al Servidor (Flask)
function disparar(ruta, id) {
    const btn = document.getElementById(id);
    const log = document.getElementById('terminal');
    const originalText = btn.innerText;

    btn.disabled = true;
    btn.innerText = "...";
    
    const time = new Date().toLocaleTimeString();
    log.innerHTML += `<br><span style="color:#999">[${time}]</span> Ejecutando orden en: ${ruta}`;

    fetch(ruta, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        log.innerHTML += `<br><span style="color:var(--naranja)">> [OK]: ${data.info}</span>`;
        // Auto-scroll al final de la consola
        log.scrollTop = log.scrollHeight;
    })
    .catch(err => {
        log.innerHTML += `<br><span style="color:red">> [ERROR]: Sin respuesta del servidor.</span>`;
    })
    .finally(() => {
        // Feedback visual de desbloqueo
        setTimeout(() => {
            btn.disabled = false;
            btn.innerText = originalText;
        }, 400);
    });
}

// 4. Reloj de Runtime (Sincronizado con el inicio del Scheduler)
function initClock() {
    const clock = document.getElementById('uptime');
    const container = document.getElementById('runtime-data');
    const startStr = container.getAttribute('data-start');
    
    // Si startStr tiene las llaves de Jinja o está vacío, usa la hora actual (modo local)
    // Caso contrario, parsea la fecha que envía Flask.
    const start = (startStr && !startStr.includes('{{')) ? new Date(startStr) : new Date();

    setInterval(() => {
        const now = new Date();
        const diff = Math.abs(now - start);

        // Cálculos de tiempo desglosados
        const msecPerDay = 24 * 60 * 60 * 1000;
        const days = Math.floor(diff / msecPerDay);
        const hours = Math.floor((diff % msecPerDay) / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);

        // Formateo con ceros a la izquierda (00:00:00:00)
        const d = days.toString().padStart(2, '0');
        const h = hours.toString().padStart(2, '0');
        const m = minutes.toString().padStart(2, '0');
        const s = seconds.toString().padStart(2, '0');

        clock.innerText = `${d}:${h}:${m}:${s}`;
    }, 1000);
}

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', initClock);