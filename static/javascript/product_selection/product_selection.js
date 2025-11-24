// Global variables
let currentProduct = null;
let selectedVariant = null;
let selectedColor = null;
let selectedSize = null;
let selectedQuantity = 1;
let selectedAddress = null;
let appliedCoupon = null;
let currentPricing = null;
let variantData = {};

// CSRF Token helper
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
}

// Modal Management
function openPurchaseModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('purchase-modal-active');
        document.body.style.overflow = 'hidden';
    }
}

function closePurchaseModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('purchase-modal-active');
        document.body.style.overflow = '';
    }
}

// Initialize purchase flow
document.addEventListener('DOMContentLoaded', function() {
    // Attach event listeners to purchase buttons
    document.querySelectorAll('.purchase-btn[data-product-id]').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            initiatePurchase(productId);
        });
    });

    // Close modal when clicking overlay
    document.querySelectorAll('.purchase-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                closePurchaseModal(this.id);
            }
        });
    });
});

// Step 1: Initiate Purchase Flow
async function initiatePurchase(productId) {
    try {
        showPurchaseLoading('Loading product details...');
        
        const response = await fetch(`/orders/products/${productId}/details/`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCSRFToken(),
            }
        });

        // Check if response is ok
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Check content type
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await response.text();
            console.error('Server returned non-JSON response:', text.substring(0, 200));
            throw new Error("Server returned non-JSON response. Please check your backend endpoint.");
        }

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success) {
            currentProduct = data;
            variantData = data.variants || {};
            displayProductSelection(data);
        } else {
            showPurchaseAlert('error', data.error || 'Failed to load product details');
        }
    } catch (error) {
        hidePurchaseLoading();
        console.error('Error in initiatePurchase:', error);
        showPurchaseAlert('error', error.message || 'please login to proceed with purchase');
    }
}

// Display Product Selection Modal
function displayProductSelection(productData) {
    const { product, colors, sizes } = productData;
    
    // Validate product data
    if (!product) {
        showPurchaseAlert('error', 'Invalid product data');
        return;
    }
    
    const modalContent = `
        <div class="purchase-product-info">
            <h3>${escapeHtml(product.name || 'Product')}</h3>
            <div class="purchase-price-display" id="purchaseCurrentPrice">
                ${product.discounted_price ? 
                    `<span class="purchase-original-price">₹${product.base_price}</span>₹${product.discounted_price}` : 
                    `₹${product.base_price || '0'}`
                }
            </div>
            <div class="purchase-stock-status" id="purchaseStockStatus">${product.total_stock || 0} items available</div>
        </div>

        ${colors && colors.length > 0 ? `
        <div class="purchase-selection-group">
            <label>Color:</label>
            <div class="purchase-color-options" id="purchaseColorOptions">
                ${colors.map(color => `
                    <button type="button" 
                            class="purchase-color-option" 
                            data-color-id="${escapeHtml(String(color.id || ''))}" 
                            style="background-color: ${escapeHtml(color.hex_code || '#ccc')}; width: 40px; height: 40px; border: 2px solid #ddd; border-radius: 50%; margin: 5px; cursor: pointer;"
                            title="${escapeHtml(color.name || 'Color')}">
                    </button>
                `).join('')}
            </div>
        </div>` : ''}

        ${sizes && sizes.length > 0 ? `
        <div class="purchase-selection-group">
            <label>Size:</label>
            <div class="purchase-size-options" id="purchaseSizeOptions">
                ${sizes.map(size => `
                    <button type="button" 
                            class="purchase-size-option" 
                            data-size-id="${escapeHtml(String(size.id || ''))}"
                            style="padding: 8px 16px; margin: 5px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px;">
                        ${escapeHtml(size.name || 'Size')}
                    </button>
                `).join('')}
            </div>
        </div>` : ''}

        <div class="purchase-selection-group">
            <label>Quantity:</label>
            <div class="purchase-quantity-selector">
                <button type="button" id="purchaseDecreaseQty" style="padding: 8px 12px; border: 1px solid #ddd; background: #f0f0f0; cursor: pointer; border-radius: 4px; color: #333;">-</button>
                <input type="number" id="purchaseQuantityInput" value="1" min="1" max="1" readonly style="width: 60px; text-align: center; border: 1px solid #ddd; margin: 0 5px;">
                <button type="button" id="purchaseIncreaseQty" style="padding: 8px 12px; border: 1px solid #ddd; background: #f0f0f0; cursor: pointer; border-radius: 4px; color: #333;">+</button>
            </div>
        </div>

        <div class="purchase-price-summary" id="purchasePriceSummary" style="display: none; margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: #f8f9fa;"></div>

        <div style="margin-top: 20px;">
            <button type="button" class="purchase-btn purchase-btn-primary" id="purchaseProceedBtn" disabled style="width: 100%; padding: 12px; border-radius: 4px; background: #FF5722; color: white; border: none; cursor: pointer; transition: background 0.3s;">
                Proceed to Review
            </button>
        </div>
    `;

    const modalContentEl = document.getElementById('purchaseProductModalContent');
    if (modalContentEl) {
        modalContentEl.innerHTML = modalContent;
        
        // Add event listeners after content is inserted
        addProductModalEventListeners(colors || [], sizes || []);
        
        openPurchaseModal('purchaseProductModal');

        // Auto-select if only one option
        if (colors && colors.length === 1 && colors[0].id) {
            selectPurchaseColor(colors[0].id);
        }
        if (sizes && sizes.length === 1 && sizes[0].id) {
            selectPurchaseSize(sizes[0].id);
        }
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add event listeners to dynamically created elements
function addProductModalEventListeners(colors, sizes) {
    // Color selection listeners using event delegation
    const colorOptions = document.getElementById('purchaseColorOptions');
    if (colorOptions) {
        colorOptions.addEventListener('click', function(e) {
            const button = e.target.closest('.purchase-color-option');
            if (button) {
                const colorId = button.getAttribute('data-color-id');
                if (colorId) {
                    selectPurchaseColor(colorId);
                }
            }
        });
    }
    
    // Size selection listeners using event delegation
    const sizeOptions = document.getElementById('purchaseSizeOptions');
    if (sizeOptions) {
        sizeOptions.addEventListener('click', function(e) {
            const button = e.target.closest('.purchase-size-option');
            if (button) {
                const sizeId = button.getAttribute('data-size-id');
                if (sizeId) {
                    selectPurchaseSize(sizeId);
                }
            }
        });
    }
    
    // Quantity listeners
    const decreaseBtn = document.getElementById('purchaseDecreaseQty');
    const increaseBtn = document.getElementById('purchaseIncreaseQty');
    const proceedBtn = document.getElementById('purchaseProceedBtn');
    
    if (decreaseBtn) {
        decreaseBtn.addEventListener('click', function() {
            updatePurchaseQuantity(-1);
        });
    }
    if (increaseBtn) {
        increaseBtn.addEventListener('click', function() {
            updatePurchaseQuantity(1);
        });
    }
    if (proceedBtn) {
        proceedBtn.addEventListener('click', function() {
            proceedToReview();
        });
    }
}

// Color Selection
function selectPurchaseColor(colorId) {
    if (!colorId) {
        console.error('Invalid colorId:', colorId);
        return;
    }
    
    selectedColor = String(colorId);
    
    // Reset selected size when color changes
    selectedSize = null;
    selectedVariant = null;
    
    // Update color UI
    document.querySelectorAll('.purchase-color-option').forEach(option => {
        option.style.border = '2px solid #ddd';
        option.style.boxShadow = 'none';
    });
    
    const selectedColorBtn = document.querySelector(`[data-color-id="${selectedColor}"]`);
    if (selectedColorBtn) {
        selectedColorBtn.style.border = '3px solid #FF5722'; /* ThinknShop Primary */
        selectedColorBtn.style.boxShadow = '0 0 0 2px rgba(255,87,34,0.25)'; /* ThinknShop Primary */
    }
    
    // Reset size selection UI
    document.querySelectorAll('.purchase-size-option').forEach(option => {
        option.style.background = 'white';
        option.style.color = '#333';
        option.style.border = '1px solid #ddd';
    });
    
    updatePurchaseSizeAvailability();
    updatePurchasePriceDisplay();
    checkPurchaseSelectionComplete();
}

// Size Selection
function selectPurchaseSize(sizeId) {
    if (!sizeId) {
        console.error('Invalid sizeId:', sizeId);
        return;
    }
    
    selectedSize = String(sizeId);
    
    // Update size UI
    document.querySelectorAll('.purchase-size-option').forEach(option => {
        option.style.background = 'white';
        option.style.color = '#333';
        option.style.border = '1px solid #ddd';
    });
    
    const selectedSizeBtn = document.querySelector(`[data-size-id="${selectedSize}"]`);
    if (selectedSizeBtn) {
        selectedSizeBtn.style.background = '#FF5722'; /* ThinknShop Primary */
        selectedSizeBtn.style.color = 'white';
        selectedSizeBtn.style.border = '1px solid #FF5722'; /* ThinknShop Primary */
    }
    
    updatePurchaseVariantInfo();
    checkPurchaseSelectionComplete();
}

// Update size availability based on selected color
function updatePurchaseSizeAvailability() {
    if (!selectedColor) return;

    document.querySelectorAll('.purchase-size-option').forEach(sizeOption => {
        const sizeId = sizeOption.getAttribute('data-size-id');
        if (!sizeId) return;
        
        const variantKey = `${selectedColor}_${sizeId}`;
        const variant = variantData[variantKey];
        
        // Reset styles
        sizeOption.disabled = false;
        sizeOption.style.opacity = '1';
        sizeOption.style.cursor = 'pointer';
        
        if (!variant || !variant.is_in_stock) {
            sizeOption.disabled = true;
            sizeOption.style.opacity = '0.5';
            sizeOption.style.cursor = 'not-allowed';
        }
    });
}

// Update variant information and pricing
function updatePurchaseVariantInfo() {
    if (!selectedColor || !selectedSize) return;

    const variantKey = `${selectedColor}_${selectedSize}`;
    selectedVariant = variantData[variantKey];
    
    if (selectedVariant) {
        // Update quantity limits
        const quantityInput = document.getElementById('purchaseQuantityInput');
        if (quantityInput) {
            const maxStock = selectedVariant.stock || 1;
            quantityInput.max = maxStock;
            if (selectedQuantity > maxStock) {
                selectedQuantity = Math.min(selectedQuantity, maxStock);
                quantityInput.value = selectedQuantity;
            }
        }
        
        updatePurchasePriceDisplay();
        calculatePurchasePrice();
    }
}

// Update price display (separate from calculation)
function updatePurchasePriceDisplay() {
    const priceEl = document.getElementById('purchaseCurrentPrice');
    const stockEl = document.getElementById('purchaseStockStatus');
    
    if (!priceEl || !stockEl) return;
    
    if (selectedVariant) {
        // Update price
        const effectivePrice = selectedVariant.effective_price || selectedVariant.price || 0;
        priceEl.innerHTML = selectedVariant.discounted_price ? 
            `<span class="purchase-original-price" style="text-decoration: line-through; color: #999; margin-right: 8px;">₹${selectedVariant.price || 0}</span> ₹${selectedVariant.discounted_price}` :
            `₹${effectivePrice}`;
        
        // Update stock
        if (!selectedVariant.is_in_stock) {
            stockEl.textContent = 'Out of Stock';
            stockEl.style.color = '#dc3545';
        } else if (selectedVariant.is_low_stock) {
            stockEl.textContent = `Only ${selectedVariant.stock || 0} left`;
            stockEl.style.color = '#fd7e14';
        } else {
            stockEl.textContent = `${selectedVariant.stock || 0} available`;
            stockEl.style.color = '#28a745';
        }
    } else if (currentProduct && currentProduct.product) {
        // Show base product info
        const product = currentProduct.product;
        priceEl.innerHTML = product.discounted_price ? 
            `<span class="purchase-original-price" style="text-decoration: line-through; color: #999; margin-right: 8px;">₹${product.base_price || 0}</span> ₹${product.discounted_price}` :
            `₹${product.base_price || 0}`;
        
        stockEl.textContent = `${product.total_stock || 0} items available`;
        stockEl.style.color = '#6c757d';
    }
}

// Quantity Management
function updatePurchaseQuantity(change) {
    if (!selectedVariant) {
        showPurchaseAlert('error', 'Please select color and size first');
        return;
    }
    
    const newQuantity = selectedQuantity + change;
    const maxStock = selectedVariant.stock || 1;
    
    if (newQuantity < 1) {
        showPurchaseAlert('error', 'Quantity cannot be less than 1');
        return;
    }
    
    if (newQuantity > maxStock) {
        showPurchaseAlert('error', `Only ${maxStock} items available`);
        return;
    }
    
    selectedQuantity = newQuantity;
    const quantityInput = document.getElementById('purchaseQuantityInput');
    if (quantityInput) {
        quantityInput.value = selectedQuantity;
    }
    
    // Recalculate price with new quantity
    calculatePurchasePrice();
}

// Check if selection is complete
function checkPurchaseSelectionComplete() {
    const proceedBtn = document.getElementById('purchaseProceedBtn');
    if (!proceedBtn) return;
    
    const isComplete = selectedColor && selectedSize && selectedVariant && selectedVariant.is_in_stock;
    proceedBtn.disabled = !isComplete;
    
    if (isComplete) {
        proceedBtn.style.opacity = '1';
        proceedBtn.style.cursor = 'pointer';
        proceedBtn.style.background = '#FF5722'; /* ThinknShop Primary */
    } else {
        proceedBtn.style.opacity = '0.6';
        proceedBtn.style.cursor = 'not-allowed';
        proceedBtn.style.background = '#FF5722'; /* Still set primary background, but faded */
    }
}

// Calculate Price via AJAX
async function calculatePurchasePrice() {
    if (!selectedVariant || !selectedVariant.id) return;

    try {
        const response = await fetch('/orders/calculate-total/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                variant_id: selectedVariant.id,
                quantity: selectedQuantity,
                coupon_code: appliedCoupon?.code || ''
            })
        });

        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            return;
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await response.text();
            console.error("Server returned non-JSON response:", text.substring(0, 200));
            return;
        }

        const data = await response.json();
        
        if (data.success && data.pricing) {
            currentPricing = data.pricing;
            displayPurchasePricingSummary(data.pricing, data.discount);
        } else {
            console.error('Price calculation failed:', data.error);
        }
    } catch (error) {
        console.error('Price calculation error:', error);
    }
}

// Display Pricing Summary
function displayPurchasePricingSummary(pricing, discount) {
    if (!pricing) return;
    
    const summaryHtml = `
        <h4 style="margin-bottom: 15px; color: #333; font-size: 16px;">Price Breakdown</h4>
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
            <span>Subtotal (${pricing.quantity || 1} ${(pricing.quantity || 1) > 1 ? 'items' : 'item'}):</span>
            <span style="font-weight: 500;">₹${pricing.subtotal || 0}</span>
        </div>
        ${discount ? `<div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #28a745; font-size: 14px;">
            <span>Discount (${escapeHtml(discount.code || '')}):</span>
            <span style="font-weight: 500;">-₹${pricing.discount_amount || 0}</span>
        </div>` : ''}
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
            <span>Shipping:</span>
            <span style="font-weight: 500; color: ${pricing.shipping_cost === '0.00' ? '#28a745' : '#333'};">
                ${pricing.shipping_cost === '0.00' ? 'FREE' : '₹' + (pricing.shipping_cost || 0)}
            </span>
        </div>
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
            <span>Tax (5% GST):</span>
            <span style="font-weight: 500;">₹${pricing.tax_amount || 0}</span>
        </div>
        <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
        <div class="purchase-price-row purchase-total" style="display: flex; justify-content: space-between; font-size: 18px; font-weight: bold; color: #333;">
            <span>Total Amount:</span>
            <span style="color: #FF5722;">₹${pricing.total_amount || 0}</span>
        </div>
    `;
    
    const priceSummary = document.getElementById('purchasePriceSummary');
    if (priceSummary) {
        priceSummary.innerHTML = summaryHtml;
        priceSummary.style.display = 'block';
    }
}

// Proceed to Address Selection
async function proceedToReview() {
    if (!selectedVariant) return;

    try {
        showPurchaseLoading('Loading addresses...');
        
        const response = await fetch('/orders/address/manage/', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCSRFToken(),
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await response.text();
            console.error('Server returned non-JSON response:', text.substring(0, 200));
            throw new Error("Server returned non-JSON response");
        }

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success) {
            displayPurchaseAddressSelection(data.addresses || []);
            closePurchaseModal('purchaseProductModal');
        } else {
            showPurchaseAlert('error', data.error || 'Failed to load addresses');
        }
    } catch (error) {
        hidePurchaseLoading();
        console.error('Error:', error);
        showPurchaseAlert('error', error.message || 'Network error occurred');
    }
}

// Display Address Selection
function displayPurchaseAddressSelection(addresses) {
    let content = '';
    
    if (!addresses || addresses.length === 0) {
        content = `
            <div class="purchase-no-addresses" style="text-align: center; padding: 40px;">
                <h4 style="margin-bottom: 20px;">No addresses found</h4>
                <button class="purchase-btn purchase-btn-primary" id="showAddAddressBtn" style="padding: 12px 24px; background: #FF5722; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.3s;">Add Address</button>
            </div>
        `;
    } else {
        content = `
            <button class="purchase-btn purchase-btn-secondary" id="showAddAddressBtn" style="margin-bottom: 20px; padding: 10px 20px; background: #607D8B; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.3s;">Add New Address</button>
            
            <div class="purchase-addresses-grid" id="purchaseAddressesGrid" style="display: grid; gap: 15px; margin-bottom: 20px;">
                ${addresses.map((address, index) => `
                    <div class="purchase-address-card" data-address-id="${escapeHtml(String(address.id || ''))}" style="border: 2px solid #ddd; padding: 15px; border-radius: 8px; cursor: pointer; transition: all 0.3s;">
                        <input type="radio" name="purchase-address" value="${escapeHtml(String(address.id || ''))}" id="address_${index}" style="margin-right: 10px;">
                        <label for="address_${index}" style="cursor: pointer; width: 100%;">
                            <h4 style="margin: 0 0 8px 0;">${escapeHtml(address.full_name || 'Name')}</h4>
                            <p style="margin: 4px 0; color: #666;">${escapeHtml(address.full_address || 'Address')}</p>
                            <p style="margin: 4px 0; color: #666;">Phone: ${escapeHtml(address.phone_number || 'N/A')}</p>
                            ${address.is_default ? '<span class="purchase-default-badge" style="display: inline-block; background: #FF5722; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-top: 8px;">Default</span>' : ''}
                        </label>
                    </div>
                `).join('')}
            </div>
            
            <div class="purchase-coupon-section" style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #f8f9fa;">
                <h4 style="margin-bottom: 10px;">Have a coupon code?</h4>
                <div class="purchase-coupon-input-group" style="display: flex; gap: 10px;">
                    <input type="text" id="purchaseCouponInput" placeholder="Enter coupon code" style="flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                    <button id="applyCouponBtn" style="padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.3s;">Apply</button>
                </div>
                <div id="purchaseCouponStatus" style="margin-top: 10px;"></div>
            </div>

            <div class="purchase-price-summary" id="purchaseReviewPriceSummary" style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #f8f9fa;">
                ${currentPricing ? generatePurchasePricingHtml(currentPricing) : ''}
            </div>
        `;
    }

    content += `
        <div class="purchase-modal-actions" style="display: flex; gap: 10px; margin-top: 20px;">
            <button class="purchase-btn purchase-btn-secondary" id="backToProductBtn" style="flex: 1; padding: 12px; background: #607D8B; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.3s;">Back</button>
            <button class="purchase-btn purchase-btn-success" id="purchasePlaceOrderBtn" disabled style="flex: 1; padding: 12px; background: #FF5722; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.3s;">
                Continue to Payment
            </button>
        </div>
    `;

    const modalContentEl = document.getElementById('purchaseAddressModalContent');
    if (modalContentEl) {
        modalContentEl.innerHTML = content;
        
        // Add event listeners using delegation and proper selectors
        addAddressModalEventListeners(addresses);
        
        openPurchaseModal('purchaseAddressModal');

        // Auto-select default address
        if (addresses && addresses.length > 0) {
            const defaultAddress = addresses.find(addr => addr.is_default);
            if (defaultAddress && defaultAddress.id) {
                selectPurchaseAddress(String(defaultAddress.id));
            }
        }
    }
}

// Add event listeners for address modal
function addAddressModalEventListeners(addresses) {
    // Add address button
    const showAddAddressBtn = document.getElementById('showAddAddressBtn');
    if (showAddAddressBtn) {
        showAddAddressBtn.addEventListener('click', showPurchaseAddAddressModal);
    }
    
    // Address selection using event delegation
    const addressesGrid = document.getElementById('purchaseAddressesGrid');
    if (addressesGrid) {
        addressesGrid.addEventListener('click', function(e) {
            const card = e.target.closest('.purchase-address-card');
            if (card) {
                const addressId = card.getAttribute('data-address-id');
                if (addressId) {
                    selectPurchaseAddress(addressId);
                }
            }
        });
    }
    
    // Apply coupon button
    const applyCouponBtn = document.getElementById('applyCouponBtn');
    if (applyCouponBtn) {
        applyCouponBtn.addEventListener('click', applyPurchaseCoupon);
    }
    
    // Back button
    const backBtn = document.getElementById('backToProductBtn');
    if (backBtn) {
        backBtn.addEventListener('click', function() {
            closePurchaseModal('purchaseAddressModal');
            openPurchaseModal('purchaseProductModal');
        });
    }
    
    // Place order button
    const placeOrderBtn = document.getElementById('purchasePlaceOrderBtn');
    if (placeOrderBtn) {
        placeOrderBtn.addEventListener('click', redirectToPurchaseOrderReview);
    }
}

// Address Selection
function selectPurchaseAddress(addressId) {
    if (!addressId) {
        console.error('Invalid addressId:', addressId);
        return;
    }
    
    selectedAddress = String(addressId);
    
    // Update UI
    document.querySelectorAll('.purchase-address-card').forEach(card => {
        card.style.border = '2px solid #ddd';
        card.style.background = 'white';
    });
    
    const selectedCard = document.querySelector(`[data-address-id="${selectedAddress}"]`);
    if (selectedCard) {
        selectedCard.style.border = '2px solid #FF5722'; /* ThinknShop Primary */
        selectedCard.style.background = '#fff8e1'; /* Light background for selection */
        
        const radioInput = selectedCard.querySelector('input[type="radio"]');
        if (radioInput) {
            radioInput.checked = true;
        }
    }
    
    const placeOrderBtn = document.getElementById('purchasePlaceOrderBtn');
    if (placeOrderBtn) {
        placeOrderBtn.disabled = false;
        placeOrderBtn.style.opacity = '1';
        placeOrderBtn.style.cursor = 'pointer';
        placeOrderBtn.style.background = '#FF5722'; /* ThinknShop Primary */
    }
}

// Apply Coupon
async function applyPurchaseCoupon() {
    const couponInput = document.getElementById('purchaseCouponInput');
    if (!couponInput) return;
    
    const couponCode = couponInput.value.trim();
    if (!couponCode) {
        showPurchaseAlert('error', 'Please enter a coupon code');
        return;
    }

    if (!selectedVariant || !selectedVariant.id) {
        showPurchaseAlert('error', 'Please select a product variant first');
        return;
    }

    try {
        showPurchaseLoading('Applying coupon...');
        
        const response = await fetch('/orders/calculate-total/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                variant_id: selectedVariant.id,
                quantity: selectedQuantity,
                coupon_code: couponCode
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            throw new Error("Server returned non-JSON response");
        }

        const data = await response.json();
        hidePurchaseLoading();

        const statusEl = document.getElementById('purchaseCouponStatus');
        if (!statusEl) return;

        if (data.success && data.discount) {
            appliedCoupon = data.discount;
            currentPricing = data.pricing;
            
            statusEl.innerHTML = 
                `<div class="purchase-alert purchase-success" style="padding: 10px; background: #d4edda; color: #155724; border-radius: 4px; margin-top: 10px;">✓ Coupon applied successfully!</div>`;
            
            const summaryEl = document.getElementById('purchaseReviewPriceSummary');
            if (summaryEl) {
                summaryEl.innerHTML = generatePurchasePricingHtml(data.pricing, data.discount);
            }
        } else {
            statusEl.innerHTML = 
                `<div class="purchase-alert purchase-error" style="padding: 10px; background: #f8d7da; color: #721c24; border-radius: 4px; margin-top: 10px;">${escapeHtml(data.error || 'Invalid coupon code')}</div>`;
        }
    } catch (error) {
        hidePurchaseLoading();
        console.error('Error:', error);
        showPurchaseAlert('error', error.message || 'Network error occurred');
    }
}

// Generate Pricing HTML
function generatePurchasePricingHtml(pricing, discount = null) {
    if (!pricing) return '';
    
    return `
        <h4 style="margin-bottom: 15px; color: #333; font-size: 16px;">Order Summary</h4>
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
            <span>Subtotal (${pricing.quantity || 1} items):</span>
            <span style="font-weight: 500;">₹${pricing.subtotal || 0}</span>
        </div>
        ${discount ? `<div class="purchase-price-row purchase-discount" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; color: #28a745;">
            <span>Discount (${escapeHtml(discount.code || '')}):</span>
            <span style="font-weight: 500;">-₹${pricing.discount_amount || 0}</span>
        </div>` : ''}
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
            <span>Shipping:</span>
            <span style="font-weight: 500; color: ${pricing.shipping_cost === '0.00' ? '#28a745' : '#333'};">${pricing.shipping_cost === '0.00' ? 'FREE' : '₹' + (pricing.shipping_cost || 0)}</span>
        </div>
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
            <span>Tax:</span>
            <span style="font-weight: 500;">₹${pricing.tax_amount || 0}</span>
        </div>
        <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
        <div class="purchase-price-row purchase-total" style="display: flex; justify-content: space-between; font-size: 18px; font-weight: bold; color: #333;">
            <span>Total:</span>
            <span style="color: #FF5722;">₹${pricing.total_amount || 0}</span>
        </div>
    `;
}

// Show Add Address Modal
function showPurchaseAddAddressModal() {
    openPurchaseModal('purchaseAddAddressModal');
}

// Save New Address
async function savePurchaseAddress() {
    const form = document.getElementById('purchaseAddAddressForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const addressData = Object.fromEntries(formData);

    try {
        showPurchaseLoading('Saving address...');
        
        const response = await fetch('/orders/manage-address/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(addressData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            throw new Error("Server returned non-JSON response");
        }

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success) {
            closePurchaseModal('purchaseAddAddressModal');
            showPurchaseAlert('success', 'Address saved successfully');
            form.reset();
            setTimeout(() => proceedToReview(), 1000);
        } else {
            showPurchaseAlert('error', data.error || 'Failed to save address');
        }
    } catch (error) {
        hidePurchaseLoading();
        console.error('Error:', error);
        showPurchaseAlert('error', error.message || 'Network error occurred');
    }
}

// Redirect to Order Review
function redirectToPurchaseOrderReview() {
    if (!selectedVariant || !selectedVariant.id || !selectedAddress) {
        showPurchaseAlert('error', 'Please complete all selections');
        return;
    }

    const params = new URLSearchParams({
        variant_id: selectedVariant.id,
        quantity: selectedQuantity,
        address_id: selectedAddress,
        coupon_code: appliedCoupon?.code || ''
    });

    window.location.href = `/orders/review/?${params.toString()}`;
}

// Utility Functions
function showPurchaseLoading(message = 'Loading...') {
    let overlay = document.getElementById('purchaseLoadingOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'purchaseLoadingOverlay';
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 9999;
            display: flex; align-items: center; justify-content: center;
        `;
        document.body.appendChild(overlay);
    }
    overlay.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 8px; text-align: center;">
            <div class="purchase-spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #FF5722; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px;"></div>
            <div style="color: #333; font-size: 16px;">${escapeHtml(message)}</div>
        </div>
    `;
    overlay.style.display = 'flex';
}

function hidePurchaseLoading() {
    const overlay = document.getElementById('purchaseLoadingOverlay');
    if (overlay) overlay.style.display = 'none';
}

function showPurchaseAlert(type, message) {
    const alert = document.createElement('div');
    alert.className = `purchase-alert purchase-${type}`;
    alert.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: flex; align-items: center; justify-content: space-between; gap: 15px;
        min-width: 300px; max-width: 500px;
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#fff3cd'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#856404'};
        border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#ffeaa7'};
    `;
    
    alert.innerHTML = `
        <span>${escapeHtml(message)}</span>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; font-size: 20px; cursor: pointer; color: inherit; padding: 0; line-height: 1;">×</button>
    `;
    
    document.body.appendChild(alert);
    setTimeout(() => {
        if (alert.parentElement) {
            alert.remove();
        }
    }, 5000);
}

// Add CSS animation for spinner
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.purchase-modal-overlay.purchase-modal-active');
        if (activeModal) {
            closePurchaseModal(activeModal.id);
        }
    }
});

// Form submission prevention
document.addEventListener('submit', function(e) {
    if (e.target.id === 'purchaseAddAddressForm') {
        e.preventDefault();
        savePurchaseAddress();
    }
});