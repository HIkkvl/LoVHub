

document.addEventListener('DOMContentLoaded', function() {
    
    //--- Устанавливаем интервал опроса: 5000 мс ---
    const REFRESH_INTERVAL = 5000;

    async function fetchComputerStatus() {
        try {
            const response = await fetch('/api/get_computers_status');
            if (!response.ok) {
                console.error("Ошибка сети при запросе статуса ПК");
                return;
            }
            
            const data = await response.json();
            
            if (data && data.computers) {
                updateTable(data.computers);
            }
            
        } catch (error) {
            console.error("Ошибка при обновлении статусов ПК:", error);
        }
    }

    function updateTable(computers) {
        const tableBody = document.getElementById('computers-table-body');
        if (!tableBody) return;

        let seenIds = new Set();

        computers.forEach(pc => {
            seenIds.add(pc.id.toString());
            
            let row = document.getElementById(`row-${pc.id}`);

            if (!row) {
                row = createNewRow(pc);
                tableBody.appendChild(row);
            }

 
            updateCell(`name-${pc.id}`, pc.name_to_display);
            updateCell(`client-${pc.id}`, pc.client);
            updateCell(`session-${pc.id}`, pc.session);
            updateCell(`start-${pc.id}`, pc.start);
            updateCell(`end-${pc.id}`, pc.end);
            updateCell(`remaining-${pc.id}`, pc.remaining);
            updateCell(`version-${pc.id}`, pc.version);


            const statusCell = document.getElementById(`status-${pc.id}`);
            if (statusCell) {
                statusCell.textContent = pc.status;
                statusCell.className = pc.status_class; 
            }
        });


        tableBody.querySelectorAll('tr').forEach(row => {
            const rowId = row.id.split('-')[1];
            if (!seenIds.has(rowId)) {
                row.style.display = 'none'; 
            }
        });
    }

    function updateCell(elementId, newText) {
        const cell = document.getElementById(elementId);
        if (cell && cell.textContent !== newText) {
            cell.textContent = newText;
        }
    }


    function createNewRow(pc) {
        const row = document.createElement('tr');
        row.id = `row-${pc.id}`;
        
        row.innerHTML = `
            <td id="name-${pc.id}">${pc.name_to_display}</td>
            <td id="status-${pc.id}" class="${pc.status_class}">${pc.status}</td>
            <td id="client-${pc.id}">${pc.client}</td>
            <td id="session-${pc.id}">${pc.session}</td>
            <td id="start-${pc.id}">${pc.start}</td>
            <td id="end-${pc.id}">${pc.end}</td>
            <td id="remaining-${pc.id}">${pc.remaining}</td>
            <td id="version-${pc.id}">${pc.version}</td>
            <td>
                <a href="/edit_pc/${pc.id}" 
                   class="add-pc-btn" 
                   style="padding: 4px 10px; font-size: 12px; text-decoration: none; background: #606060;">
                    Переименовать
                </a>
            </td>
        `;
        return row;
    }


    fetchComputerStatus();
    

    setInterval(fetchComputerStatus, REFRESH_INTERVAL);

});