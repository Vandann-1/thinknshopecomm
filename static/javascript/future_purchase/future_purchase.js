/**
 * Future Purchase Management System
 * Handles product scheduling with custom modals and AJAX
 */

class FuturePurchaseManager {
    constructor() {
        this.currentProduct = null;
        this.modal = null;
        this.isLoading = false;
        
        // Initialize on DOM ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    init() {
        this.createModalStyles();
        this.setupEventListeners();
    }
    
    /**
     * Create custom modal styles
     */
    createModalStyles() {
        const styleId = 'future-purchase-modal-styles';
        if (document.getElementById(styleId)) return;
        
        const styles = `
            .fp-modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }
            
            .fp-modal-overlay.active {
                opacity: 1;
                visibility: visible;
            }
            
            .fp-modal {
                background: white;
                border-radius: 16px;
                max-width: 600px;
                width: 90%;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                transform: scale(0.9) translateY(20px);
                transition: all 0.3s ease;
                position: relative;
            }
            
            .fp-modal-overlay.active .fp-modal {
                transform: scale(1) translateY(0);
            }
            
            .dark .fp-modal {
                background: rgb(31, 41, 55);
                color: white;
            }
            
            .fp-modal-header {
                padding: 24px 24px 0;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .dark .fp-modal-header {
                border-bottom-color: #374151;
            }
            
            .fp-modal-close {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #6b7280;
                transition: color 0.2s ease;
                padding: 8px;
                border-radius: 8px;
            }
            
            .fp-modal-close:hover {
                color: #374151;
                background-color: #f3f4f6;
            }
            
            .dark .fp-modal-close:hover {
                color: #d1d5db;
                background-color: #374151;
            }
            
            .fp-modal-body {
                padding: 24px;
            }
            
            .fp-form-group {
                margin-bottom: 20px;
            }
            
            .fp-form-label {
                display: block;
                margin-bottom: 6px;
                font-weight: 500;
                color: #374151;
            }
            
            .dark .fp-form-label {
                color: #d1d5db;
            }
            
            .fp-form-input,
            .fp-form-select,
            .fp-form-textarea {
                width: 100%;
                padding: 12px 16px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                transition: all 0.2s ease;
                background: white;
            }
            
            .dark .fp-form-input,
            .dark .fp-form-select,
            .dark .fp-form-textarea {
                background: rgb(55, 65, 81);
                border-color: #4b5563;
                color: white;
            }
            
            .fp-form-input:focus,
            .fp-form-select:focus,
            .fp-form-textarea:focus {
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }
            
            .fp-form-checkbox {
                margin-right: 8px;
            }
            
            .fp-form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
            
            .fp-product-info {
                background: #f9fafb;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 16px;
            }
            
            .dark .fp-product-info {
                background: rgb(55, 65, 81);
            }
            
            .fp-product-image {
                width: 80px;
                height: 80px;
                object-fit: cover;
                border-radius: 8px;
                background: #e5e7eb;
            }
            
            .fp-product-details h3 {
                margin: 0 0 8px 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .fp-product-price {
                font-size: 16px;
                font-weight: 600;
                color: #059669;
            }
            
            .fp-modal-footer {
                padding: 24px;
                border-top: 1px solid #e5e7eb;
                display: flex;
                gap: 12px;
                justify-content: flex-end;
            }
            
            .dark .fp-modal-footer {
                border-top-color: #374151;
            }
            
            .fp-btn {
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                border: none;
                font-size: 14px;
            }
            
            .fp-btn-primary {
                background: #3b82f6;
                color: white;
            }
            
            .fp-btn-primary:hover:not(:disabled) {
                background: #2563eb;
            }
            
            .fp-btn-secondary {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
            }
            
            .fp-btn-secondary:hover {
                background: #e5e7eb;
            }
            
            .dark .fp-btn-secondary {
                background: rgb(55, 65, 81);
                color: white;
                border-color: #4b5563;
            }
            
            .fp-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .fp-loading-spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #ffffff;
                border-radius: 50%;
                border-top-color: transparent;
                animation: spin 1s ease-in-out infinite;
                margin-right: 8px;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .fp-error-message {
                background: #fef2f2;
                border: 1px solid #fecaca;
                color: #dc2626;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 16px;
                font-size: 14px;
            }
            
            .dark .fp-error-message {
                background: rgba(220, 38, 38, 0.1);
                border-color: rgba(220, 38, 38, 0.3);
            }
            
            .fp-success-message {
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                color: #059669;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 16px;
                font-size: 14px;
            }
            
            .dark .fp-success-message {
                background: rgba(5, 150, 105, 0.1);
                border-color: rgba(5, 150, 105, 0.3);
            }
            
            .fp-estimated-total {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                padding: 12px;
                border-radius: 8px;
                margin-top: 16px;
                text-align: center;
                font-weight: 600;
                color: #1d4ed8;
            }
            
            .dark .fp-estimated-total {
                background: rgba(29, 78, 216, 0.1);
                border-color: rgba(29, 78, 216, 0.3);
            }
            
            @media (max-width: 640px) {
                .fp-modal {
                    width: 95%;
                    margin: 20px;
                }
                
                .fp-form-row {
                    grid-template-columns: 1fr;
                }
                
                .fp-modal-footer {
                    flex-direction: column;
                }
                
                .fp-btn {
                    width: 100%;
                }
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = styleId;
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
    
    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal) {
                this.closeModal();
            }
        });
    }
    
    /**
     * Main function to schedule a purchase
     */
    async schedulePurchase(productId) {
        if (this.isLoading) return;
        
        try {
            this.isLoading = true;
            this.showLoadingToast('Loading product details...');
            
            // Fetch product details
            const response = await fetch(`/schedule_purchase/api/products/${productId}/details/`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load product details');
            }
            
            this.currentProduct = data.product;
            this.showModal();
            
        } catch (error) {
            console.error('Error fetching product details:', error);
            this.showErrorToast(error.message || 'Failed to load product details');
        } finally {
            this.isLoading = false;
            this.hideLoadingToast();
        }
    }
    
    /**
     * Show the future purchase modal
     */
    showModal() {
        if (!this.currentProduct) return;
        
        this.modal = this.createModal();
        document.body.appendChild(this.modal);
        
        // Trigger animation
        requestAnimationFrame(() => {
            this.modal.classList.add('active');
        });
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
        
        // Setup form interactions
        this.setupFormInteractions();
    }
    
    /**
     * Create the modal HTML structure
     */
    createModal() {
        const overlay = document.createElement('div');
        overlay.className = 'fp-modal-overlay';
        
        const currentDate = new Date();
        const minDate = new Date(currentDate.getTime() + 24 * 60 * 60 * 1000); // Tomorrow
        const minDateStr = minDate.toISOString().slice(0, 16);
        
        overlay.innerHTML = `
            <div class="fp-modal">
                <div class="fp-modal-header">
                    <h2 style="margin: 0; font-size: 20px; font-weight: 600;">Schedule Future Purchase</h2>
                    <button type="button" class="fp-modal-close" onclick="futurePurchaseManager.closeModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="fp-modal-body">
                    <div id="fp-message-container"></div>
                    
                    <!-- Product Info -->
                    <div class="fp-product-info">
                        <img src="${this.currentProduct.image_url || '/static/images/no-image.png'}" 
                             alt="${this.currentProduct.name}" 
                             class="fp-product-image">
                        <div class="fp-product-details">
                            <h3>${this.currentProduct.name}</h3>
                            <div class="fp-product-price">$${this.currentProduct.base_price}</div>
                            <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                                ${this.currentProduct.is_in_stock ? '✅ In Stock' : '❌ Out of Stock'}
                            </div>
                        </div>
                    </div>
                    
                    <form id="fp-form">
                        <!-- Basic Details -->
                        <div class="fp-form-group">
                            <label class="fp-form-label" for="fp-title">Custom Title (Optional)</label>
                            <input type="text" 
                                   id="fp-title" 
                                   name="title" 
                                   class="fp-form-input" 
                                   placeholder="My custom purchase title">
                        </div>
                        
                        <!-- Variant Selection -->
                        ${this.currentProduct.has_variants ? this.createVariantSelection() : ''}
                        
                        <div class="fp-form-row">
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-quantity">Quantity *</label>
                                <input type="number" 
                                       id="fp-quantity" 
                                       name="quantity" 
                                       class="fp-form-input" 
                                       min="1" 
                                       value="1" 
                                       required>
                            </div>
                            
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-scheduled-date">Schedule Date *</label>
                                <input type="datetime-local" 
                                       id="fp-scheduled-date" 
                                       name="scheduled_date" 
                                       class="fp-form-input" 
                                       min="${minDateStr}" 
                                       required>
                            </div>
                        </div>
                        
                        <div class="fp-form-row">
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-frequency">Frequency</label>
                                <select id="fp-frequency" name="frequency" class="fp-form-select">
                                    <option value="once">One Time</option>
                                    <option value="weekly">Weekly</option>
                                    <option value="biweekly">Bi-Weekly</option>
                                    <option value="monthly">Monthly</option>
                                    <option value="quarterly">Quarterly</option>
                                    <option value="yearly">Yearly</option>
                                </select>
                            </div>
                            
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-action-type">Action Type</label>
                                <select id="fp-action-type" name="action_type" class="fp-form-select">
                                    <option value="reminder">Email Reminder Only</option>
                                    <option value="auto_purchase">Automatic Purchase</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="fp-form-row">
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-priority">Priority</label>
                                <select id="fp-priority" name="priority" class="fp-form-select">
                                    <option value="low">Low</option>
                                    <option value="medium" selected>Medium</option>
                                    <option value="high">High</option>
                                    <option value="urgent">Urgent</option>
                                </select>
                            </div>
                            
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-reminder-days">Reminder Days Before</label>
                                <input type="number" 
                                       id="fp-reminder-days" 
                                       name="reminder_days_before" 
                                       class="fp-form-input" 
                                       min="0" 
                                       value="1">
                            </div>
                        </div>
                        
                        <!-- Price Limits -->
                        <div class="fp-form-row">
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-max-price">Max Price (Optional)</label>
                                <input type="number" 
                                       id="fp-max-price" 
                                       name="max_price" 
                                       class="fp-form-input" 
                                       step="0.01" 
                                       placeholder="0.00">
                            </div>
                            
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-budget-limit">Budget Limit (Optional)</label>
                                <input type="number" 
                                       id="fp-budget-limit" 
                                       name="budget_limit" 
                                       class="fp-form-input" 
                                       step="0.01" 
                                       placeholder="0.00">
                            </div>
                        </div>
                        
                        <!-- Recurring Settings -->
                        <div id="fp-recurring-settings" style="display: none;">
                            <div class="fp-form-group">
                                <label class="fp-form-label" for="fp-max-executions">Max Executions (Optional)</label>
                                <input type="number" 
                                       id="fp-max-executions" 
                                       name="max_executions" 
                                       class="fp-form-input" 
                                       min="1" 
                                       placeholder="Leave empty for unlimited">
                            </div>
                        </div>
                        
                        <!-- Options -->
                        <div class="fp-form-group">
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" 
                                       id="fp-send-reminder" 
                                       name="send_reminder_email" 
                                       class="fp-form-checkbox" 
                                       checked>
                                <span class="fp-form-label" style="margin: 0;">Send Email Reminder</span>
                            </label>
                        </div>
                        
                        <div id="fp-auto-purchase-settings" style="display: none;">
                            <div class="fp-form-group">
                                <label style="display: flex; align-items: center; cursor: pointer;">
                                    <input type="checkbox" 
                                           id="fp-check-stock" 
                                           name="check_stock_availability" 
                                           class="fp-form-checkbox" 
                                           checked>
                                    <span class="fp-form-label" style="margin: 0;">Check Stock Before Purchase</span>
                                </label>
                            </div>
                            
                            <div class="fp-form-group">
                                <label style="display: flex; align-items: center; cursor: pointer;">
                                    <input type="checkbox" 
                                           id="fp-use-default-address" 
                                           name="use_default_address" 
                                           class="fp-form-checkbox" 
                                           checked>
                                    <span class="fp-form-label" style="margin: 0;">Use Default Shipping Address</span>
                                </label>
                            </div>
                            
                            <div class="fp-form-group" id="fp-custom-address-group" style="display: none;">
                                <label class="fp-form-label" for="fp-shipping-address">Custom Shipping Address</label>
                                <textarea id="fp-shipping-address" 
                                          name="shipping_address" 
                                          class="fp-form-textarea" 
                                          rows="3" 
                                          placeholder="Enter custom shipping address..."></textarea>
                            </div>
                        </div>
                        
                        <!-- Notes -->
                        <div class="fp-form-group">
                            <label class="fp-form-label" for="fp-notes">Notes (Optional)</label>
                            <textarea id="fp-notes" 
                                      name="notes" 
                                      class="fp-form-textarea" 
                                      rows="3" 
                                      placeholder="Any special notes or instructions..."></textarea>
                        </div>
                        
                        <!-- Estimated Total -->
                        <div id="fp-estimated-total" class="fp-estimated-total">
                            <div>Estimated Total: <span id="fp-total-amount">${this.currentProduct.base_price}</span></div>
                        </div>
                    </form>
                </div>
                
                <div class="fp-modal-footer">
                    <button type="button" class="fp-btn fp-btn-secondary" onclick="futurePurchaseManager.closeModal()">
                        Cancel
                    </button>
                    <button type="button" class="fp-btn fp-btn-primary" onclick="futurePurchaseManager.submitForm()" id="fp-submit-btn">
                        Schedule Purchase
                    </button>
                </div>
            </div>
        `;
        
        // Close modal on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.closeModal();
            }
        });
        
        return overlay;
    }
    
    /**
     * Create variant selection HTML
     */
    createVariantSelection() {
        let html = '<div class="fp-form-group"><label class="fp-form-label" for="fp-variant">Select Variant</label><select id="fp-variant" name="variant_id" class="fp-form-select"><option value="">Default Variant</option>';
        
        this.currentProduct.variants.forEach(variant => {
            const stockText = variant.is_in_stock ? '✅' : '❌';
            const price = variant.price !== this.currentProduct.base_price ? ` - ${variant.price}` : '';
            html += `<option value="${variant.id}" ${!variant.is_in_stock ? 'disabled' : ''}>
                ${stockText} ${variant.color} - ${variant.size}${price}
            </option>`;
        });
        
        html += '</select></div>';
        return html;
    }
    
    /**
     * Setup form interactions and validations
     */
    setupFormInteractions() {
        // Handle frequency changes
        const frequencySelect = document.getElementById('fp-frequency');
        const recurringSettings = document.getElementById('fp-recurring-settings');
        
        frequencySelect.addEventListener('change', () => {
            if (frequencySelect.value === 'once') {
                recurringSettings.style.display = 'none';
            } else {
                recurringSettings.style.display = 'block';
            }
        });
        
        // Handle action type changes
        const actionTypeSelect = document.getElementById('fp-action-type');
        const autoPurchaseSettings = document.getElementById('fp-auto-purchase-settings');
        
        actionTypeSelect.addEventListener('change', () => {
            if (actionTypeSelect.value === 'auto_purchase') {
                autoPurchaseSettings.style.display = 'block';
            } else {
                autoPurchaseSettings.style.display = 'none';
            }
        });
        
        // Handle default address checkbox
        const useDefaultAddress = document.getElementById('fp-use-default-address');
        const customAddressGroup = document.getElementById('fp-custom-address-group');
        
        if (useDefaultAddress) {
            useDefaultAddress.addEventListener('change', () => {
                if (useDefaultAddress.checked) {
                    customAddressGroup.style.display = 'none';
                } else {
                    customAddressGroup.style.display = 'block';
                }
            });
        }
        
        // Update estimated total on quantity/variant changes
        const quantityInput = document.getElementById('fp-quantity');
        const variantSelect = document.getElementById('fp-variant');
        
        const updateEstimatedTotal = () => {
            const quantity = parseInt(quantityInput.value) || 1;
            let price = parseFloat(this.currentProduct.base_price);
            
            if (variantSelect && variantSelect.value) {
                const selectedVariant = this.currentProduct.variants.find(v => v.id == variantSelect.value);
                if (selectedVariant) {
                    price = parseFloat(selectedVariant.price);
                }
            }
            
            const total = (price * quantity).toFixed(2);
            document.getElementById('fp-total-amount').textContent = `${total}`;
        };
        
        quantityInput.addEventListener('input', updateEstimatedTotal);
        if (variantSelect) {
            variantSelect.addEventListener('change', updateEstimatedTotal);
        }
        
        // Set default scheduled date (tomorrow at current time)
        const scheduledDateInput = document.getElementById('fp-scheduled-date');
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        scheduledDateInput.value = tomorrow.toISOString().slice(0, 16);
    }
    
    /**
     * Submit the future purchase form
     */
    async submitForm() {
        if (this.isLoading) return;
        
        const submitBtn = document.getElementById('fp-submit-btn');
        const form = document.getElementById('fp-form');
        const messageContainer = document.getElementById('fp-message-container');
        
        try {
            this.isLoading = true;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="fp-loading-spinner"></span>Scheduling...';
            
            // Clear previous messages
            messageContainer.innerHTML = '';
            
            // Collect form data
            const formData = new FormData(form);
            const data = {
                product_id: this.currentProduct.id,
                title: formData.get('title') || '',
                variant_id: formData.get('variant_id') || null,
                quantity: parseInt(formData.get('quantity')) || 1,
                scheduled_date: formData.get('scheduled_date'),
                frequency: formData.get('frequency') || 'once',
                action_type: formData.get('action_type') || 'reminder',
                priority: formData.get('priority') || 'medium',
                reminder_days_before: parseInt(formData.get('reminder_days_before')) || 1,
                max_price: formData.get('max_price') ? parseFloat(formData.get('max_price')) : null,
                budget_limit: formData.get('budget_limit') ? parseFloat(formData.get('budget_limit')) : null,
                max_executions: formData.get('max_executions') ? parseInt(formData.get('max_executions')) : null,
                send_reminder_email: formData.get('send_reminder_email') === 'on',
                auto_purchase_enabled: formData.get('action_type') === 'auto_purchase',
                check_stock_availability: formData.get('check_stock_availability') === 'on',
                use_default_address: formData.get('use_default_address') === 'on',
                shipping_address: formData.get('shipping_address') || '',
                notes: formData.get('notes') || ''
            };
            
            // Validate required fields
            if (!data.scheduled_date) {
                throw new Error('Please select a scheduled date');
            }
            
            if (data.quantity < 1) {
                throw new Error('Quantity must be at least 1');
            }
            
            // Submit to server
            const response = await fetch('/schedule_purchase/api/future-purchases/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to schedule purchase');
            }
            
            // Show success message
            messageContainer.innerHTML = `
                <div class="fp-success-message">
                    <i class="fas fa-check-circle"></i> ${result.message}
                </div>
            `;
            
            // Update button
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Scheduled!';
            submitBtn.style.background = '#059669';
            
            // Close modal after delay
            setTimeout(() => {
                this.closeModal();
                this.showSuccessToast('Future purchase scheduled successfully!');
            }, 1500);
            
        } catch (error) {
            console.error('Error submitting future purchase:', error);
            
            // Show error message
            messageContainer.innerHTML = `
                <div class="fp-error-message">
                    <i class="fas fa-exclamation-triangle"></i> ${error.message}
                </div>
            `;
            
            // Reset button
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Schedule Purchase';
            
        } finally {
            this.isLoading = false;
        }
    }
    
    /**
     * Close the modal
     */
    closeModal() {
        if (!this.modal) return;
        
        this.modal.classList.remove('active');
        
        setTimeout(() => {
            if (this.modal && this.modal.parentNode) {
                this.modal.parentNode.removeChild(this.modal);
            }
            this.modal = null;
            this.currentProduct = null;
            
            // Restore body scroll
            document.body.style.overflow = '';
        }, 300);
    }
    
    /**
     * Get CSRF token for Django
     */
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfInput ? csrfInput.value : '';
    }
    
    /**
     * Show loading toast
     */
    showLoadingToast(message) {
        this.removeExistingToasts();
        
        const toast = document.createElement('div');
        toast.id = 'fp-loading-toast';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #3b82f6;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 14px;
        `;
        
        toast.innerHTML = `
            <span class="fp-loading-spinner" style="margin-right: 8px;"></span>
            ${message}
        `;
        
        document.body.appendChild(toast);
    }
    
    /**
     * Hide loading toast
     */
    hideLoadingToast() {
        const toast = document.getElementById('fp-loading-toast');
        if (toast) {
            toast.remove();
        }
    }
    
    /**
     * Show success toast
     */
    showSuccessToast(message) {
        this.removeExistingToasts();
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #059669;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 14px;
            animation: slideIn 0.3s ease;
        `;
        
        toast.innerHTML = `
            <i class="fas fa-check-circle" style="margin-right: 8px;"></i>
            ${message}
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    /**
     * Show error toast
     */
    showErrorToast(message) {
        this.removeExistingToasts();
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc2626;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 14px;
            animation: slideIn 0.3s ease;
        `;
        
        toast.innerHTML = `
            <i class="fas fa-exclamation-triangle" style="margin-right: 8px;"></i>
            ${message}
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
    /**
     * Remove existing toasts
     */
    removeExistingToasts() {
        const existingToasts = document.querySelectorAll('[id*="toast"], #fp-loading-toast');
        existingToasts.forEach(toast => toast.remove());
    }
    
    /**
     * Get user's future purchases
     */
    async getUserFuturePurchases() {
        try {
            const response = await fetch('/schedule_purchase/api/future-purchases/user/');
            const data = await response.json();
            
            if (data.success) {
                return data.future_purchases;
            } else {
                throw new Error(data.error || 'Failed to fetch future purchases');
            }
        } catch (error) {
            console.error('Error fetching future purchases:', error);
            throw error;
        }
    }
    
    /**
     * Update future purchase status
     */
    async updatePurchaseStatus(purchaseId, action) {
        try {
            const response = await fetch(`/schedule_purchase/api/future-purchases/${purchaseId}/status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ action })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccessToast(data.message);
                return data;
            } else {
                throw new Error(data.error || 'Failed to update purchase status');
            }
        } catch (error) {
            console.error('Error updating purchase status:', error);
            this.showErrorToast(error.message);
            throw error;
        }
    }
}

// Add CSS animations
const animationStyles = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;

const animationStyleSheet = document.createElement('style');
animationStyleSheet.textContent = animationStyles;
document.head.appendChild(animationStyleSheet);

// Initialize the manager
const futurePurchaseManager = new FuturePurchaseManager();

// Global function for the button onclick
function schedulePurchase(productId) {
    futurePurchaseManager.schedulePurchase(productId);
}