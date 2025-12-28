class AddressManager {
    constructor() {
        console.log('🚀 AddressManager: Constructor called');
        this.currentAddressId = null;
        this.deleteAddressId = null;
        this.init();
    }

    init() {
        console.log('🔧 AddressManager: Initializing...');
        this.bindEvents();
        this.setupFormValidation();
        console.log('✅ AddressManager: Initialization complete');
    }

    bindEvents() {
        console.log('🔗 AddressManager: Binding events...');
        
        // Modal triggers
        const addAddressBtn = document.getElementById('addAddressBtn');
        const addFirstAddressBtn = document.getElementById('addFirstAddressBtn');
        
        if (addAddressBtn) {
            addAddressBtn.addEventListener('click', (e) => {
                console.log('🖱️ addAddressBtn clicked!');
                this.openAddModal();
            });
        }
        
        if (addFirstAddressBtn) {
            addFirstAddressBtn.addEventListener('click', (e) => {
                console.log('🖱️ addFirstAddressBtn clicked!');
                this.openAddModal();
            });
        }
        
        // Modal close
        const closeModalBtn = document.getElementById('closeModalBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.closeModal());
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeModal());
        }
        
        // Form submission
        const addressForm = document.getElementById('addressForm');
        if (addressForm) {
            addressForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
        
        // Delete modal
        const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        
        if (cancelDeleteBtn) {
            cancelDeleteBtn.addEventListener('click', () => this.closeDeleteModal());
        }
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => this.confirmDelete());
        }
        
        // Address card actions
        document.querySelectorAll('.edit-address-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.editAddress(e.target.dataset.addressId);
            });
        });
        
        document.querySelectorAll('.delete-address-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.openDeleteModal(e.target.dataset.addressId);
            });
        });
        
        document.querySelectorAll('.set-default-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setDefaultAddress(e.target.dataset.addressId);
            });
        });
        
        // Pincode lookup
        const pincodeField = document.getElementById('pincode');
        if (pincodeField) {
            pincodeField.addEventListener('blur', (e) => {
                this.lookupPincode(e.target.value);
            });
        }
        
        // Apartment checkbox
        const isApartmentField = document.getElementById('isApartment');
        if (isApartmentField) {
            isApartmentField.addEventListener('change', (e) => {
                this.toggleFloorSection(e.target.checked);
            });
        }
        
        // Modal backdrop clicks
        const addressModal = document.getElementById('addressModal');
        const deleteModal = document.getElementById('deleteModal');
        
        if (addressModal) {
            addressModal.addEventListener('click', (e) => {
                if (e.target.id === 'addressModal') {
                    this.closeModal();
                }
            });
        }
        
        if (deleteModal) {
            deleteModal.addEventListener('click', (e) => {
                if (e.target.id === 'deleteModal') {
                    this.closeDeleteModal();
                }
            });
        }
        
        console.log('✅ Event binding complete');
    }

    setupFormValidation() {
        console.log('📋 Setting up form validation...');
        // Only validate fields that actually exist
        const possibleFields = ['label', 'fullName', 'phoneNumber', 'addressLine1', 'pincode', 'city', 'state'];
        
        possibleFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('blur', () => this.validateField(field));
                field.addEventListener('input', () => this.clearFieldError(field));
            }
        });
        console.log('✅ Form validation setup complete');
    }

    validateField(field) {
        const value = field.value.trim();
        const isValid = value.length > 0;
        
        if (!isValid) {
            this.showFieldError(field, 'This field is required');
        } else {
            this.clearFieldError(field);
        }
        
        return isValid;
    }

    showFieldError(field, message) {
        field.classList.add('border-red-500');
        field.classList.remove('border-gray-300');
        
        let errorDiv = field.parentNode.querySelector('.field-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'field-error text-red-500 text-sm mt-1';
            field.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    clearFieldError(field) {
        field.classList.remove('border-red-500');
        field.classList.add('border-gray-300');
        const errorDiv = field.parentNode.querySelector('.field-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    openAddModal() {
        console.log('🚪 Opening add modal...');
        
        this.currentAddressId = null;
        const modalTitle = document.getElementById('modalTitle');
        const submitBtnText = document.getElementById('submitBtnText');
        
        if (modalTitle) modalTitle.textContent = 'Add New Address';
        if (submitBtnText) submitBtnText.textContent = 'Save Address';
        
        this.resetForm();
        this.showModal();
        
        console.log('✅ Add modal opened successfully');
    }

    editAddress(addressId) {
        console.log('✏️ Editing address:', addressId);
        
        if (!addressId) {
            console.error('❌ No address ID provided');
            return;
        }
        
        this.currentAddressId = addressId;
        const modalTitle = document.getElementById('modalTitle');
        const submitBtnText = document.getElementById('submitBtnText');
        
        if (modalTitle) modalTitle.textContent = 'Edit Address';
        if (submitBtnText) submitBtnText.textContent = 'Update Address';
        
        // Show modal first, then load data
        this.showModal();
        
        // Load address data after modal is shown
        setTimeout(() => {
            this.loadAddressData(addressId);
        }, 150);
    }

    async loadAddressData(addressId) {
        console.log('📥 Loading address data for ID:', addressId);
        
        try {
            const response = await fetch(`/address/get-details/?address_id=${addressId}`);
            const data = await response.json();
            
            console.log('📊 Received address data:', data);
            
            if (data.success) {
                // Add a small delay to ensure modal is fully rendered
                setTimeout(() => {
                    this.populateForm(data.address);
                }, 100);
            } else {
                console.error('❌ Server returned error:', data);
                this.showToast('Error loading address data', 'error');
            }
        } catch (error) {
            console.error('💥 Error loading address:', error);
            this.showToast('Failed to load address data', 'error');
        }
    }

    populateForm(address) {
        console.log('📝 Populating form with address data:', address);
        
        // Clear any existing errors first
        this.resetForm();
        
        // Common field mappings - adjust these based on your actual HTML field IDs
        const fieldMappings = {
            // Basic fields
            'label': address.label,
            'fullName': address.full_name,
            'phoneNumber': address.phone_number,
            'alternatePhone': address.alternate_phone,
            'addressLine1': address.address_line_1,
            'addressLine2': address.address_line_2,
            'landmark': address.landmark,
            'pincode': address.pincode,
            'city': address.city,
            'state': address.state,
            'deliveryInstructions': address.delivery_instructions,
            'floorNumber': address.floor_number,
            
            // Alternative field names (in case your HTML uses different IDs)
            'address_line_1': address.address_line_1,
            'address_line_2': address.address_line_2,
            'phone_number': address.phone_number,
            'alternate_phone': address.alternate_phone,
            'full_name': address.full_name,
            'delivery_instructions': address.delivery_instructions,
            'floor_number': address.floor_number,
            
            // Hidden field for address ID
            'addressId': address.id,
            'address_id': address.id
        };
        
        // Populate text fields
        Object.entries(fieldMappings).forEach(([fieldId, value]) => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.value = value || '';
                console.log(`✅ Set ${fieldId} = "${value || ''}"`);
                // Clear any validation errors for this field
                this.clearFieldError(field);
            } else {
                console.log(`⚠️ Field '${fieldId}' not found in DOM`);
            }
        });
        
        // Handle dropdown/select fields
        const addressTypeField = document.getElementById('addressType');
        if (addressTypeField && address.address_type) {
            addressTypeField.value = address.address_type;
            console.log(`✅ Set addressType = "${address.address_type}"`);
        }
        
        // Handle checkboxes
        const isApartmentField = document.getElementById('isApartment');
        if (isApartmentField) {
            isApartmentField.checked = Boolean(address.is_apartment);
            console.log(`✅ Set isApartment = ${Boolean(address.is_apartment)}`);
            // Trigger floor section toggle
            this.toggleFloorSection(Boolean(address.is_apartment));
        }
        
        const isDefaultField = document.getElementById('isDefault');
        if (isDefaultField) {
            isDefaultField.checked = Boolean(address.is_default);
            console.log(`✅ Set isDefault = ${Boolean(address.is_default)}`);
        }
        
        // Debug: List all available form fields
        console.log('🔍 Available form fields:');
        const form = document.getElementById('addressForm');
        if (form) {
            const formElements = form.querySelectorAll('input, select, textarea');
            formElements.forEach(element => {
                if (element.id) {
                    console.log(`  - ${element.id}: ${element.tagName} (${element.type || 'N/A'})`);
                }
            });
        }
        
        console.log('✅ Form population completed');
    }

    resetForm() {
        console.log('🔄 Resetting form...');
        
        const form = document.getElementById('addressForm');
        if (form) {
            form.reset();
        }
        
        const addressIdField = document.getElementById('addressId');
        if (addressIdField) {
            addressIdField.value = '';
        }
        
        this.toggleFloorSection(false);
        
        // Clear all field errors
        document.querySelectorAll('.field-error').forEach(error => error.remove());
        document.querySelectorAll('.border-red-500').forEach(field => {
            field.classList.remove('border-red-500');
            field.classList.add('border-gray-300');
        });
        
        console.log('✅ Form reset complete');
    }

    showModal() {
        console.log('👁️ Showing modal...');
        
        const modal = document.getElementById('addressModal');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            console.log('✅ Modal should now be visible');
        } else {
            console.error('❌ addressModal element not found!');
        }
    }

    closeModal() {
        console.log('🚪 Closing modal...');
        
        const modal = document.getElementById('addressModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
            console.log('✅ Modal closed');
        }
    }

    toggleFloorSection(show) {
        console.log('🏢 Toggling floor section:', show);
        
        const floorSection = document.getElementById('floorSection');
        if (floorSection) {
            if (show) {
                floorSection.classList.remove('hidden');
            } else {
                floorSection.classList.add('hidden');
                const floorNumberField = document.getElementById('floorNumber');
                if (floorNumberField) floorNumberField.value = '';
            }
        }
    }

    async lookupPincode(pincode) {
        console.log('📍 Looking up pincode:', pincode);
        
        if (!pincode || pincode.length !== 6) {
            return;
        }
        
        const loader = document.getElementById('pincodeLoader');
        if (loader) loader.classList.remove('hidden');
        
        try {
            const response = await fetch(`/address/pincode-lookup/?pincode=${pincode}`);
            const data = await response.json();
            
            if (data.success) {
                const cityField = document.getElementById('city');
                const stateField = document.getElementById('state');
                
                if (cityField) cityField.value = data.data.city;
                if (stateField) stateField.value = data.data.state;
                
                if (!data.data.is_serviceable) {
                    this.showToast('This pincode may not be serviceable', 'warning');
                }
            } else {
                this.showToast('Invalid pincode or data not found', 'error');
            }
        } catch (error) {
            console.error('💥 Pincode lookup error:', error);
        } finally {
            if (loader) loader.classList.add('hidden');
        }
    }

    async handleFormSubmit(e) {
        console.log('📝 Handling form submit...');
        e.preventDefault();
        
        if (!this.validateForm()) {
            console.log('❌ Form validation failed');
            return;
        }
        
        this.setSubmitLoading(true);
        
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        
        // Handle checkboxes
        data.is_apartment = document.getElementById('isApartment')?.checked || false;
        data.is_default = document.getElementById('isDefault')?.checked || false;
        
        if (this.currentAddressId) {
            data.address_id = this.currentAddressId;
        }
        
        console.log('📊 Form data to submit:', data);
        
        try {
            const response = await fetch('/address/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast(result.message, 'success');
                this.closeModal();
                this.refreshAddressList();
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            console.error('💥 Save error:', error);
            this.showToast('Failed to save address', 'error');
        } finally {
            this.setSubmitLoading(false);
        }
    }

    validateForm() {
        console.log('✅ Validating form...');
        
        // Only validate essential fields that actually exist
        const essentialFields = ['fullName', 'phoneNumber', 'addressLine1', 'pincode'];
        let isValid = true;
        let missingFields = [];
        
        essentialFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                if (!field.value.trim()) {
                    this.showFieldError(field, 'This field is required');
                    isValid = false;
                    missingFields.push(fieldId);
                } else {
                    this.clearFieldError(field);
                }
            } else {
                console.log(`⚠️ Field '${fieldId}' not found - skipping validation`);
            }
        });
        
        // Simple phone validation (if field exists)
        const phoneField = document.getElementById('phoneNumber');
        if (phoneField && phoneField.value.trim()) {
            const phoneValue = phoneField.value.trim();
            if (!/^\d{10}$/.test(phoneValue)) {
                this.showFieldError(phoneField, 'Please enter a valid 10-digit phone number');
                isValid = false;
            }
        }
        
        // Simple pincode validation (if field exists)
        const pincodeField = document.getElementById('pincode');
        if (pincodeField && pincodeField.value.trim()) {
            const pincodeValue = pincodeField.value.trim();
            if (!/^\d{6}$/.test(pincodeValue)) {
                this.showFieldError(pincodeField, 'Please enter a valid 6-digit pincode');
                isValid = false;
            }
        }
        
        if (!isValid) {
            console.log('❌ Validation failed for fields:', missingFields);
        } else {
            console.log('✅ Form validation passed');
        }
        
        return isValid;
    }

    setSubmitLoading(loading) {
        const submitBtn = document.getElementById('submitBtn');
        const submitBtnText = document.getElementById('submitBtnText');
        const submitLoader = document.getElementById('submitLoader');
        
        if (loading) {
            if (submitBtn) submitBtn.disabled = true;
            if (submitBtnText) submitBtnText.classList.add('hidden');
            if (submitLoader) submitLoader.classList.remove('hidden');
        } else {
            if (submitBtn) submitBtn.disabled = false;
            if (submitBtnText) submitBtnText.classList.remove('hidden');
            if (submitLoader) submitLoader.classList.add('hidden');
        }
    }

    openDeleteModal(addressId) {
        console.log('🗑️ Opening delete modal for address:', addressId);
        
        this.deleteAddressId = addressId;
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    closeDeleteModal() {
        console.log('🚪 Closing delete modal...');
        
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
        }
        this.deleteAddressId = null;
    }

    async confirmDelete() {
        console.log('🗑️ Confirming delete for address:', this.deleteAddressId);
        
        if (!this.deleteAddressId) return;
        
        try {
            const response = await fetch('/address/delete/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ address_id: this.deleteAddressId })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast(result.message, 'success');
                this.closeDeleteModal();
                this.refreshAddressList();
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            console.error('💥 Delete error:', error);
            this.showToast('Failed to delete address', 'error');
        }
    }

    async setDefaultAddress(addressId) {
        console.log('⭐ Setting default address:', addressId);
        
        try {
            const response = await fetch('/address/set-default/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ address_id: addressId })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast(result.message, 'success');
                this.refreshAddressList();
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            console.error('💥 Set default error:', error);
            this.showToast('Failed to set default address', 'error');
        }
    }

    refreshAddressList() {
        console.log('🔄 Refreshing address list...');
        window.location.reload();
    }

    // Debug method to help identify field mapping issues
    debugFormFields() {
        console.log('🐛 DEBUG: Form field analysis');
        const form = document.getElementById('addressForm');
        if (!form) {
            console.log('❌ Form not found');
            return;
        }
        
        const fields = form.querySelectorAll('input, select, textarea');
        console.log(`📋 Found ${fields.length} form fields:`);
        
        fields.forEach(field => {
            console.log(`  - ID: "${field.id || 'NO_ID'}", Name: "${field.name || 'NO_NAME'}", Type: "${field.type || field.tagName}"${field.required ? ' (REQUIRED)' : ''}`);
        });
    }

    showToast(message, type = 'info') {
        console.log('🍞 Showing toast:', message, type);
        
        const toast = document.createElement('div');
        const baseClasses = 'px-4 py-3 rounded-lg shadow-lg border transform transition-all duration-300 translate-x-full';
        
        let typeClasses;
        switch (type) {
            case 'success':
                typeClasses = 'bg-green-50 border-green-200 text-green-800';
                break;
            case 'error':
                typeClasses = 'bg-red-50 border-red-200 text-red-800';
                break;
            case 'warning':
                typeClasses = 'bg-yellow-50 border-yellow-200 text-yellow-800';
                break;
            default:
                typeClasses = 'bg-blue-50 border-blue-200 text-blue-800';
        }
        
        toast.className = `${baseClasses} ${typeClasses}`;
        toast.textContent = message;
        
        const container = document.getElementById('toastContainer');
        if (container) {
            container.appendChild(toast);
            
            // Animate in
            setTimeout(() => {
                toast.classList.remove('translate-x-full');
            }, 100);
            
            // Auto remove
            setTimeout(() => {
                toast.classList.add('translate-x-full');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }, 5000);
            
            // Click to dismiss
            toast.addEventListener('click', () => {
                toast.classList.add('translate-x-full');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            });
        } else {
            // Fallback to alert if no toast container
            alert(message);
        }
    }
}

// Initialize the address manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎬 DOM Content Loaded - Initializing AddressManager...');
    new AddressManager();
});

// Utility function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add CSRF token to all fetch requests
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    if (options.method && options.method.toUpperCase() !== 'GET') {
        options.headers = options.headers || {};
        options.headers['X-CSRFToken'] = getCookie('csrftoken');
    }
    return originalFetch(url, options);
};