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

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success) {
            currentProduct = data;
            variantData = data.variants;
            displayProductSelection(data);
        } else {
            showPurchaseAlert('error', data.error || 'Failed to load product details');
        }
    } catch (error) {
        hidePurchaseLoading();
        showPurchaseAlert('error', 'Network error occurred');
        console.error('Error:', error);
    }
}

// Display Product Selection Modal
function displayProductSelection(productData) {
    const { product, colors, sizes } = productData;
    
    const modalContent = `
        <div class="purchase-product-info">
            <h3>${product.name}</h3>
            <div class="purchase-price-display" id="purchaseCurrentPrice">
                ${product.discounted_price ? 
                    `<span class="purchase-original-price">₹${product.base_price}</span>₹${product.discounted_price}` : 
                    `₹${product.base_price}`
                }
            </div>
            <div class="purchase-stock-status" id="purchaseStockStatus">${product.total_stock} items available</div>
        </div>

        ${colors.length > 0 ? `
        <div class="purchase-selection-group">
            <label>Color:</label>
            <div class="purchase-color-options" id="purchaseColorOptions">
                ${colors.map(color => `
                    <button type="button" class="purchase-color-option" data-purchase-color-id="${color.id}" 
                            style="background-color: ${color.hex_code}; width: 30px; height: 30px; border: 2px solid #ddd; border-radius: 50%; margin: 5px; cursor: pointer;"
                            title="${color.name}">
                    </button>
                `).join('')}
            </div>
        </div>` : ''}

        ${sizes.length > 0 ? `
        <div class="purchase-selection-group">
            <label>Size:</label>
            <div class="purchase-size-options" id="purchaseSizeOptions">
                ${sizes.map(size => `
                    <button type="button" class="purchase-size-option" data-purchase-size-id="${size.id}"
                            style="padding: 8px 16px; margin: 5px; border: 1px solid #ddd; background: white; cursor: pointer;">
                        ${size.name}
                    </button>
                `).join('')}
            </div>
        </div>` : ''}

        <div class="purchase-selection-group">
            <label>Quantity:</label>
            <div class="purchase-quantity-selector">
                <button type="button" id="purchaseDecreaseQty" style="padding: 8px 12px; border: 1px solid #ddd; background: white; cursor: pointer;">-</button>
                <input type="number" id="purchaseQuantityInput" value="1" min="1" max="1" readonly style="width: 60px; text-align: center; border: 1px solid #ddd; margin: 0 5px;">
                <button type="button" id="purchaseIncreaseQty" style="padding: 8px 12px; border: 1px solid #ddd; background: white; cursor: pointer;">+</button>
            </div>
        </div>

        <div class="purchase-price-summary" id="purchasePriceSummary" style="display: none; margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px;"></div>

        <div style="margin-top: 20px;">
            <button type="button" class="purchase-btn purchase-btn-primary" id="purchaseProceedBtn" disabled style="width: 100%; padding: 12px;">
                Proceed to Review
            </button>
        </div>
    `;

    document.getElementById('purchaseProductModalContent').innerHTML = modalContent;
    
    // Add event listeners after content is inserted
    addProductModalEventListeners(colors, sizes);
    
    openPurchaseModal('purchaseProductModal');

    // Auto-select if only one option
    if (colors.length === 1) selectPurchaseColor(colors[0].id);
    if (sizes.length === 1) selectPurchaseSize(sizes[0].id);
}

// Add event listeners to dynamically created elements
function addProductModalEventListeners(colors, sizes) {
    // Color selection listeners
    colors.forEach(color => {
        const colorBtn = document.querySelector(`[data-purchase-color-id="${color.id}"]`);
        if (colorBtn) {
            colorBtn.addEventListener('click', () => selectPurchaseColor(color.id));
        }
    });
    
    // Size selection listeners  
    sizes.forEach(size => {
        const sizeBtn = document.querySelector(`[data-purchase-size-id="${size.id}"]`);
        if (sizeBtn) {
            sizeBtn.addEventListener('click', () => selectPurchaseSize(size.id));
        }
    });
    
    // Quantity listeners
    const decreaseBtn = document.getElementById('purchaseDecreaseQty');
    const increaseBtn = document.getElementById('purchaseIncreaseQty');
    const proceedBtn = document.getElementById('purchaseProceedBtn');
    
    if (decreaseBtn) decreaseBtn.addEventListener('click', () => updatePurchaseQuantity(-1));
    if (increaseBtn) increaseBtn.addEventListener('click', () => updatePurchaseQuantity(1));
    if (proceedBtn) proceedBtn.addEventListener('click', proceedToReview);
}

// Color Selection
function selectPurchaseColor(colorId) {
    selectedColor = colorId;
    
    // Reset selected size when color changes
    selectedSize = null;
    selectedVariant = null;
    
    // Update color UI
    document.querySelectorAll('.purchase-color-option').forEach(option => {
        option.style.border = '2px solid #ddd';
    });
    const selectedColorBtn = document.querySelector(`[data-purchase-color-id="${colorId}"]`);
    if (selectedColorBtn) {
        selectedColorBtn.style.border = '2px solid #007bff';
    }
    
    // Reset size selection UI
    document.querySelectorAll('.purchase-size-option').forEach(option => {
        option.style.background = 'white';
        option.style.border = '1px solid #ddd';
    });
    
    updatePurchaseSizeAvailability();
    updatePurchasePriceDisplay();
    checkPurchaseSelectionComplete();
}

// Size Selection
function selectPurchaseSize(sizeId) {
    selectedSize = sizeId;
    
    // Update size UI
    document.querySelectorAll('.purchase-size-option').forEach(option => {
        option.style.background = 'white';
        option.style.border = '1px solid #ddd';
    });
    const selectedSizeBtn = document.querySelector(`[data-purchase-size-id="${sizeId}"]`);
    if (selectedSizeBtn) {
        selectedSizeBtn.style.background = '#007bff';
        selectedSizeBtn.style.color = 'white';
        selectedSizeBtn.style.border = '1px solid #007bff';
    }
    
    updatePurchaseVariantInfo();
    checkPurchaseSelectionComplete();
}

// Update size availability based on selected color
function updatePurchaseSizeAvailability() {
    if (!selectedColor) return;

    document.querySelectorAll('.purchase-size-option').forEach(sizeOption => {
        const sizeId = sizeOption.getAttribute('data-purchase-size-id');
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
            quantityInput.max = selectedVariant.stock;
            if (selectedQuantity > selectedVariant.stock) {
                selectedQuantity = selectedVariant.stock;
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
        priceEl.innerHTML = selectedVariant.discounted_price ? 
            `<span class="purchase-original-price" style="text-decoration: line-through; color: #999;">₹${selectedVariant.price}</span> ₹${selectedVariant.discounted_price}` :
            `₹${selectedVariant.effective_price}`;
        
        // Update stock
        if (!selectedVariant.is_in_stock) {
            stockEl.textContent = 'Out of Stock';
            stockEl.style.color = '#dc3545';
        } else if (selectedVariant.is_low_stock) {
            stockEl.textContent = `Only ${selectedVariant.stock} left`;
            stockEl.style.color = '#fd7e14';
        } else {
            stockEl.textContent = `${selectedVariant.stock} available`;
            stockEl.style.color = '#28a745';
        }
    } else {
        // Show base product info
        const product = currentProduct.product;
        priceEl.innerHTML = product.discounted_price ? 
            `<span class="purchase-original-price" style="text-decoration: line-through; color: #999;">₹${product.base_price}</span> ₹${product.discounted_price}` :
            `₹${product.base_price}`;
        
        stockEl.textContent = `${product.total_stock} items available`;
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
    const maxStock = selectedVariant.stock;
    
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
    } else {
        proceedBtn.style.opacity = '0.6';
        proceedBtn.style.cursor = 'not-allowed';
    }
}

// Calculate Price via AJAX
async function calculatePurchasePrice() {
    if (!selectedVariant) return;

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

        const data = await response.json();
        
        if (data.success) {
            currentPricing = data.pricing;
            displayPurchasePricingSummary(data.pricing, data.discount);
        }
    } catch (error) {
        console.error('Price calculation error:', error);
    }
}

// Display Pricing Summary
function displayPurchasePricingSummary(pricing, discount) {
    const summaryHtml = `
        <h4 style="margin-bottom: 15px; color: #333;">Price Breakdown</h4>
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span>Subtotal (${pricing.quantity} ${pricing.quantity > 1 ? 'items' : 'item'}):</span>
            <span style="font-weight: 500;">₹${pricing.subtotal}</span>
        </div>
        ${discount ? `<div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #28a745;">
            <span>Discount (${discount.code}):</span>
            <span style="font-weight: 500;">-₹${pricing.discount_amount}</span>
        </div>` : ''}
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span>Shipping:</span>
            <span style="font-weight: 500; color: ${pricing.shipping_cost === '0.00' ? '#28a745' : '#333'};">
                ${pricing.shipping_cost === '0.00' ? 'FREE' : '₹' + pricing.shipping_cost}
            </span>
        </div>
        <div class="purchase-price-row" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span>Tax (5% GST):</span>
            <span style="font-weight: 500;">₹${pricing.tax_amount}</span>
        </div>
        <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
        <div class="purchase-price-row purchase-total" style="display: flex; justify-content: space-between; font-size: 18px; font-weight: bold; color: #333;">
            <span>Total Amount:</span>
            <span style="color: #007bff;">₹${pricing.total_amount}</span>
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

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success) {
            displayPurchaseAddressSelection(data.addresses);
            closePurchaseModal('purchaseProductModal');
        } else {
            showPurchaseAlert('error', data.error || 'Failed to load addresses');
        }
    } catch (error) {
        hidePurchaseLoading();
        showPurchaseAlert('error', 'Network error occurred');
    }
}

// Display Address Selection
function displayPurchaseAddressSelection(addresses) {
    let content = '';
    
    if (addresses.length === 0) {
        content = `
            <div class="purchase-no-addresses">
                <h4>No addresses found</h4>
                <button class="purchase-btn purchase-btn-primary" onclick="showPurchaseAddAddressModal()">Add Address</button>
            </div>
        `;
    } else {
        content = `
            <button class="purchase-btn purchase-btn-secondary" onclick="showPurchaseAddAddressModal()">Add New Address</button>
            
            <div class="purchase-addresses-grid">
                ${addresses.map(address => `
                    <div class="purchase-address-card" onclick="selectPurchaseAddress('${address.id}')">
                        <input type="radio" name="purchase-address" value="${address.id}">
                        <div>
                            <h4>${address.full_name}</h4>
                            <p>${address.full_address}</p>
                            <p>Phone: ${address.phone_number}</p>
                            ${address.is_default ? '<span class="purchase-default-badge">Default</span>' : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
            
            <div class="purchase-coupon-section">
                <h4>Have a coupon code?</h4>
                <div class="purchase-coupon-input-group">
                    <input type="text" id="purchaseCouponInput" placeholder="Enter coupon code">
                    <button onclick="applyPurchaseCoupon()">Apply</button>
                </div>
                <div id="purchaseCouponStatus"></div>
            </div>

            <div class="purchase-price-summary" id="purchaseReviewPriceSummary">
                ${currentPricing ? generatePurchasePricingHtml(currentPricing) : ''}
            </div>
        `;
    }

content += `
    <div class="purchase-modal-actions">
        <button class="purchase-btn purchase-btn-secondary"
            onclick="closePurchaseModal('purchaseAddressModal')">
            Back
        </button>

        <button class="purchase-btn bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-300"
            id="purchasePlaceOrderBtn"
            onclick="redirectToPurchaseOrderReview()"
            disabled>
            Continue to Payment
        </button>
    </div>
`;


    document.getElementById('purchaseAddressModalContent').innerHTML = content;
    openPurchaseModal('purchaseAddressModal');

    // Auto-select default address
    const defaultAddress = addresses.find(addr => addr.is_default);
    if (defaultAddress) selectPurchaseAddress(defaultAddress.id);
}

// Address Selection
function selectPurchaseAddress(addressId) {
    selectedAddress = addressId;
    
    document.querySelectorAll('.purchase-address-card').forEach(card => {
        card.classList.remove('purchase-selected');
    });
    
    const selectedCard = document.querySelector(`[onclick*="${addressId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('purchase-selected');
        selectedCard.querySelector('input').checked = true;
    }
    
    document.getElementById('purchasePlaceOrderBtn').disabled = false;
}

// Apply Coupon
async function applyPurchaseCoupon() {
    const couponCode = document.getElementById('purchaseCouponInput').value.trim();
    if (!couponCode) return;

    try {
        showPurchaseLoading('Applying coupon...');
        
        // Recalculate with coupon
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

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success && data.discount) {
            appliedCoupon = data.discount;
            currentPricing = data.pricing;
            
            document.getElementById('purchaseCouponStatus').innerHTML = 
                `<div class="purchase-alert purchase-success">✓ Coupon applied successfully!</div>`;
            
            document.getElementById('purchaseReviewPriceSummary').innerHTML = generatePurchasePricingHtml(data.pricing, data.discount);
        } else {
            document.getElementById('purchaseCouponStatus').innerHTML = 
                `<div class="purchase-alert purchase-error">${data.error || 'Invalid coupon code'}</div>`;
        }
    } catch (error) {
        hidePurchaseLoading();
        showPurchaseAlert('error', 'Network error occurred');
    }
}

// Generate Pricing HTML
function generatePurchasePricingHtml(pricing, discount = null) {
    return `
        <div class="purchase-price-row">
            <span>Subtotal (${pricing.quantity} items):</span>
            <span>₹${pricing.subtotal}</span>
        </div>
        ${discount ? `<div class="purchase-price-row purchase-discount">
            <span>Discount (${discount.code}):</span>
            <span>-₹${pricing.discount_amount}</span>
        </div>` : ''}
        <div class="purchase-price-row">
            <span>Shipping:</span>
            <span>${pricing.shipping_cost === '0.00' ? 'FREE' : '₹' + pricing.shipping_cost}</span>
        </div>
        <div class="purchase-price-row">
            <span>Tax:</span>
            <span>₹${pricing.tax_amount}</span>
        </div>
        <div class="purchase-price-row purchase-total">
            <span>Total:</span>
            <span>₹${pricing.total_amount}</span>
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

        const data = await response.json();
        hidePurchaseLoading();

        if (data.success) {
            closePurchaseModal('purchaseAddAddressModal');
            showPurchaseAlert('success', 'Address saved successfully');
            form.reset();
            setTimeout(() => proceedToReview(), 1000);
        } else {
            showPurchaseAlert('error', data.error);
        }
    } catch (error) {
        hidePurchaseLoading();
        showPurchaseAlert('error', 'Network error occurred');
    }
}

// Redirect to Order Review
function redirectToPurchaseOrderReview() {
    if (!selectedVariant || !selectedAddress) return;

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
            background: rgba(255,255,255,0.9); z-index: 9999;
            display: flex; align-items: center; justify-content: center;
        `;
        document.body.appendChild(overlay);
    }
    overlay.innerHTML = `<div><div class="purchase-spinner"></div><div>${message}</div></div>`;
    overlay.style.display = 'flex';
}

function hidePurchaseLoading() {
    const overlay = document.getElementById('purchaseLoadingOverlay');
    if (overlay) overlay.style.display = 'none';
}

function showPurchaseAlert(type, message) {
    const alert = document.createElement('div');
    alert.className = `purchase-alert purchase-${type}`;
    alert.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()">×</button>`;
    document.body.insertBefore(alert, document.body.firstChild);
    setTimeout(() => alert.remove(), 5000);
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.purchase-modal-overlay.purchase-modal-active');
        if (activeModal) closePurchaseModal(activeModal.id);
    }
});

// Form submission prevention
document.addEventListener('submit', function(e) {
    if (e.target.id === 'purchaseAddAddressForm') {
        e.preventDefault();
        savePurchaseAddress();
    }
});