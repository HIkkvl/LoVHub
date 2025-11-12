

document.addEventListener('DOMContentLoaded', function() {
    

    const container = document.getElementById('apps-container');
    const iconBaseUrl = container.dataset.iconBaseUrl || '/static/icons/';
    const csrfToken = container.dataset.csrfToken || '';
    
    const editCsrfInput = document.getElementById('edit_csrf_token');
    if (editCsrfInput) {
        editCsrfInput.value = csrfToken;
    }


    const addModal = document.getElementById('addAppModal');
    const openAddBtn = document.getElementById('openAddModalBtn');
    const closeAddBtn = document.getElementById('closeAddModalBtn');

    if(openAddBtn) {
        openAddBtn.onclick = function() { addModal.style.display = 'block'; }
    }
    if(closeAddBtn) {
        closeAddBtn.onclick = function() { addModal.style.display = 'none'; }
    }


    const editModal = document.getElementById('editAppModal');
    const closeEditBtn = document.getElementById('closeEditModalBtn');
    const editForm = document.getElementById('editAppForm');
    
    const editNameField = document.getElementById('edit_name');
    const editPathField = document.getElementById('edit_path');
    const editTypeHiddenField = document.getElementById('edit_type_hidden'); 
    const editIconFileInput = document.getElementById('edit_icon_file_input');
    const editImageUploadArea = document.getElementById('edit-image-upload-area');
    const editImagePreview = editImageUploadArea.querySelector('.preview');
    const editUploadIcon = editImageUploadArea.querySelector('.upload-icon');
    const editUploadText = editImageUploadArea.querySelector('.upload-text');

    const editButtons = document.querySelectorAll('.btn-edit-app');
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const appId = this.getAttribute('data-app-id');
            
            editForm.action = `/edit/${appId}`; 
            editIconFileInput.value = ""; 

            editImagePreview.style.display = 'none';
            editUploadIcon.style.display = 'block';
            editUploadText.style.display = 'block';

            fetch(`/api/app_details/${appId}`)
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        editNameField.value = result.data.name;
                        editPathField.value = result.data.path;
                        editTypeHiddenField.value = result.data.type; 

                        if (result.data.icon) {
                            editImagePreview.src = iconBaseUrl + result.data.icon;
                            editImagePreview.style.display = 'block';
                            editUploadIcon.style.display = 'none';
                            editUploadText.style.display = 'none';
                        }
                        
                        editModal.style.display = 'block';
                    } else {
                        alert('Ошибка: ' + result.message);
                    }
                })
                .catch(err => {
                    console.error('Ошибка fetch:', err);
                    alert('Не удалось загрузить данные приложения.');
                });
        });
    });

    if(closeEditBtn) {
        closeEditBtn.onclick = function() { editModal.style.display = 'none'; }
    }

    window.onclick = function(event) {
        if (event.target == addModal) {
            addModal.style.display = 'none';
        }
        if (event.target == editModal) {
            editModal.style.display = 'none';
        }
    }

    const tabs = document.querySelectorAll('.tab-link');
    const lists = document.querySelectorAll('.app-list'); 

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            lists.forEach(list => {
                list.style.display = 'none';
            });
            document.getElementById(tabId).style.display = 'flex';
        });
    });

    function setupImageUpload(fileInputId, imageUploadAreaId) {
        const fileInput = document.getElementById(fileInputId);
        const uploadArea = document.getElementById(imageUploadAreaId);
        const previewImage = uploadArea.querySelector('.preview');
        const uploadIcon = uploadArea.querySelector('.upload-icon');
        const uploadText = uploadArea.querySelector('.upload-text');

        if (uploadArea) {
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });
        }

        if (fileInput) {
            fileInput.addEventListener('change', function() {
                if (this.files && this.files[0]) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewImage.src = e.target.result;
                        previewImage.style.display = 'block';
                        uploadIcon.style.display = 'none';
                        uploadText.style.display = 'none';
                    };
                    reader.readAsDataURL(this.files[0]);
                } else {
                    previewImage.style.display = 'none';
                    previewImage.src = '#'; 
                    uploadIcon.style.display = 'block';
                    uploadText.style.display = 'block';
                }
            });
        }
    }

    setupImageUpload('add_icon_file_input', 'add-image-upload-area');
    setupImageUpload('edit_icon_file_input', 'edit-image-upload-area');

});