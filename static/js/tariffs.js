

document.addEventListener('DOMContentLoaded', function() {
    
    const container = document.getElementById('tariffs-container');
    const csrfToken = container.dataset.csrfToken || '';
    
    const editCsrfInput = document.getElementById('edit_csrf_token');
    if (editCsrfInput) {
        editCsrfInput.value = csrfToken;
    }

    const addModal = document.getElementById('addTariffModal');
    const openAddBtn = document.getElementById('openTariffModalBtn');
    const closeAddBtn = document.getElementById('closeAddModalBtn');

    if(openAddBtn) {
        openAddBtn.onclick = function() {
            addModal.style.display = 'block';
        }
    }
    if(closeAddBtn) {
        closeAddBtn.onclick = function() {
            addModal.style.display = 'none';
        }
    }

    const editModal = document.getElementById('editTariffModal');
    const closeEditBtn = document.getElementById('closeEditModalBtn');
    const editForm = document.getElementById('editTariffForm');
    
    const editNameField = document.getElementById('edit_name');
    const editDurationField = document.getElementById('edit_duration_text');
    const editPriceCommonField = document.getElementById('edit_price_common');
    const editPriceVipField = document.getElementById('edit_price_vip');
    const editScheduleTextField = document.getElementById('edit_schedule_text');
    const editScheduleIconsField = document.getElementById('edit_schedule_icons');
    const editIsActiveCheck = document.getElementById('edit_is_active');

    const editButtons = document.querySelectorAll('.btn-edit-tariff');
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tariffId = this.getAttribute('data-tariff-id');
            
            editForm.action = `/edit_tariff/${tariffId}`; 
            
            fetch(`/api/tariff_details/${tariffId}`)
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        const data = result.data;
                        
                        editNameField.value = data.name;
                        editDurationField.value = data.duration_text;
                        editPriceCommonField.value = data.price_common;
                        editPriceVipField.value = data.price_vip;
                        editScheduleTextField.value = data.schedule_text;
                        editScheduleIconsField.value = data.schedule_icons;

                        editIsActiveCheck.checked = data.is_active; 
                        
                        editModal.style.display = 'block';
                    } else {
                        alert('Ошибка: ' + result.message);
                    }
                })
                .catch(err => {
                    console.error('Ошибка fetch:', err);
                    alert('Не удалось загрузить данные тарифа.');
                });
        });
    });

    if(closeEditBtn) {
        closeEditBtn.onclick = function() {
            editModal.style.display = 'none';
        }
    }


    window.onclick = function(event) {
        if (event.target == addModal) {
            addModal.style.display = 'none';
        }
        if (event.target == editModal) {
            editModal.style.display = 'none';
        }
    }

    // (Здесь в будущем добавлю логику для вкладок "Активные", "Скидки" и т.д.)
});