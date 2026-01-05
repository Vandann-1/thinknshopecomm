// Isolated E-commerce Cart Modal System
// Usage: EcommerceCartModal.fillProductIntoCart(productId)

const EcommerceCartModal = (function() {
    'use strict';
    
    // Private state - isolated from global scope
    let currentModal = null;
    let selectedVariant = null;
    let currentProduct = null;
    let selectedColor = null;
    let selectedSize = null;
    let currentQuantity = 1;
    let availableStock = 0;
    let escKeyHandler = null;
    
    // Private utility functions
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
    
    function generateUniqueId(prefix) {
        return prefix + '_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    // Toast system with unique IDs
    function createToastContainer() {
        const containerId = 'ecomToastContainer_' + Date.now();
        const container = document.createElement('div');
        container.id = containerId;
        container.className = 'ecom-toast-container fixed top-4 right-4 z-50 flex flex-col gap-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }
    
    function showToast(type, title, message, duration = 5000) {
        const toastContainer = document.querySelector('.ecom-toast-container') || createToastContainer();
        const toastId = generateUniqueId('ecomToast');
        
        const iconClass = type === 'success' ? 'fa-check-circle text-green-400' : 'fa-exclamation-circle text-red-400';
        const borderClass = type === 'success' ? 'border-l-green-400' : 'border-l-red-400';
        
        const toastHtml = `
            <div class="ecom-toast flex items-center gap-4 bg-gray-900 border border-gray-700 ${borderClass} border-l-4 rounded-lg p-4 shadow-2xl transform translate-x-full opacity-0 transition-all duration-300 ease-out max-w-md" id="${toastId}">
                <div class="flex-shrink-0">
                    <i class="fas ${iconClass} text-xl"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-white font-semibold text-sm">${title}</div>
                    <div class="text-gray-300 text-sm mt-1">${message}</div>
                </div>
                <button class="flex-shrink-0 text-gray-400 hover:text-white transition-colors duration-200" onclick="EcommerceCartModal.removeToast('${toastId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toast = document.getElementById(toastId);
        
        // Show toast
        setTimeout(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
            toast.classList.add('translate-x-0', 'opacity-100');
        }, 10);
        
        // Auto remove
        setTimeout(() => {
            removeToast(toastId);
        }, duration);
    }
    
    function removeToast(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => {
                toast.remove();
                
                // Clean up container if empty
                const container = document.querySelector('.ecom-toast-container');
                if (container && container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }
    }
    
    // Modal functions
    function showVariantModal(data) {
        // Reset state
        currentProduct = data.product;
        selectedColor = null;
        selectedSize = null;
        selectedVariant = null;
        currentQuantity = 1;
        availableStock = 0;
        
        const modalId = generateUniqueId('ecomModal');
        const priceId = generateUniqueId('currentPrice');
        const colorErrorId = generateUniqueId('colorError');
        const sizeErrorId = generateUniqueId('sizeError');
        const stockInfoId = generateUniqueId('stockInfo');
        const quantityInputId = generateUniqueId('quantityInput');
        const decreaseBtnId = generateUniqueId('decreaseBtn');
        const increaseBtnId = generateUniqueId('increaseBtn');
        const addToCartBtnId = generateUniqueId('addToCartBtn');

        const modalHtml = `
            <div class="ecom-modal fixed inset-0 flex items-center justify-center p-4 bg-black bg-opacity-75 backdrop-blur-sm opacity-0 transition-all duration-300 ease-out" id="${modalId}" style="z-index: 10000;">
                <div class="relative w-full max-w-2xl bg-gray-900 rounded-2xl shadow-2xl transform scale-95 transition-all duration-300 ease-out border border-gray-700">
                    <!-- Modal Header -->
                    <div class="flex items-center justify-between p-6 border-b border-gray-700">
                        <div>
                            <h2 class="text-2xl font-bold text-white">Select Options</h2>
                            <p class="text-sm text-gray-400 mt-1">Choose your preferred variant</p>
                        </div>
                        <button class="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-full transition-all duration-200" onclick="EcommerceCartModal.closeModal()">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>

                    <!-- Modal Body -->
                    <div class="p-6 max-h-96 overflow-y-auto">
                        <!-- Product Info -->
                        <div class="flex gap-6 mb-8">
                            <div class="flex-shrink-0">
                                <img src="${data.product.image || '/static/images/placeholder.jpg'}" 
                                     alt="${data.product.name}" 
                                     class="w-24 h-24 object-cover rounded-xl border border-gray-700">
                            </div>
                            <div class="flex-1">
                                <h3 class="text-xl font-semibold text-white mb-2">${data.product.name}</h3>
                                <div class="text-3xl font-bold text-blue-400 mb-2" id="${priceId}">₹${data.product.base_price}</div>
                                <p class="text-gray-400 text-sm">Please select your preferred options below.</p>
                            </div>
                        </div>

                        ${data.colors && data.colors.length > 0 ? `
                        <!-- Color Selection -->
                        <div class="mb-8">
                            <label class="block text-lg font-semibold text-white mb-4">
                                <i class="fas fa-palette mr-2 text-blue-400"></i>Color
                            </label>
                            <div class="flex flex-wrap gap-3">
                                ${data.colors.map(color => `
                                    <div class="relative group">
                                        <div class="ecom-color-option w-12 h-12 rounded-full border-2 border-gray-600 cursor-pointer transition-all duration-200 hover:scale-110 hover:border-blue-400 hover:shadow-lg hover:shadow-blue-400/25" 
                                             style="background-color: ${color.hex_code}" 
                                             data-ecom-color-id="${color.id}"
                                             title="${color.name}"
                                             onclick="EcommerceCartModal.selectColor(${color.id})">
                                        </div>
                                        <span class="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap">${color.name}</span>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="hidden items-center gap-2 mt-3 text-red-400 text-sm" id="${colorErrorId}">
                                <i class="fas fa-exclamation-circle"></i>
                                <span>Please select a color</span>
                            </div>
                        </div>
                        ` : ''}

                        ${data.sizes && data.sizes.length > 0 ? `
                        <!-- Size Selection -->
                        <div class="mb-8">
                            <label class="block text-lg font-semibold text-white mb-4">
                                <i class="fas fa-ruler mr-2 text-blue-400"></i>Size
                            </label>
                            <div class="grid grid-cols-4 gap-3">
                                ${data.sizes.map(size => `
                                    <button class="ecom-size-option px-4 py-3 bg-gray-800 text-white rounded-lg border border-gray-600 hover:border-blue-400 hover:bg-gray-700 transition-all duration-200 hover:transform hover:-translate-y-1 hover:shadow-lg hover:shadow-blue-600/25 font-medium" 
                                            data-ecom-size-id="${size.id}"
                                            onclick="EcommerceCartModal.selectSize(${size.id})">
                                        ${size.name}
                                    </button>
                                `).join('')}
                            </div>
                            <div class="hidden items-center gap-2 mt-3 text-red-400 text-sm" id="${sizeErrorId}">
                                <i class="fas fa-exclamation-circle"></i>
                                <span>Please select a size</span>
                            </div>
                        </div>
                        ` : ''}

                        <!-- Quantity Selection -->
                        <div class="mb-6">
                            <label class="block text-lg font-semibold text-white mb-4">
                                <i class="fas fa-hashtag mr-2 text-blue-400"></i>Quantity
                            </label>
                            <div class="flex items-center gap-4">
                                <div class="flex items-center bg-gray-800 rounded-lg border border-gray-700">
                                    <button class="p-3 text-white hover:bg-gray-700 rounded-l-lg transition-all duration-200 hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed" 
                                            onclick="EcommerceCartModal.decreaseQuantity()" id="${decreaseBtnId}">
                                        <i class="fas fa-minus"></i>
                                    </button>
                                    <input type="number" 
                                           class="w-16 text-center bg-transparent text-white font-semibold py-3 border-0 focus:outline-none" 
                                           id="${quantityInputId}" 
                                           value="1" min="1" 
                                           onchange="EcommerceCartModal.updateQuantity(this.value)">
                                    <button class="p-3 text-white hover:bg-gray-700 rounded-r-lg transition-all duration-200 hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed" 
                                            onclick="EcommerceCartModal.increaseQuantity()" id="${increaseBtnId}">
                                        <i class="fas fa-plus"></i>
                                    </button>
                                </div>
                                <div class="flex items-center gap-2">
                                    <i class="fas fa-box text-gray-400"></i>
                                    <span class="text-gray-400 font-medium" id="${stockInfoId}">Select options to see availability</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Modal Footer -->
                    <div class="flex items-center justify-between p-6 border-t border-gray-700 bg-gray-800/50 rounded-b-2xl">
                        <button class="px-6 py-3 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-all duration-200 font-medium border border-gray-600 hover:border-gray-500" 
                                onclick="EcommerceCartModal.closeModal()">
                            <i class="fas fa-times mr-2"></i>Cancel
                        </button>
                        <button class="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all duration-200 font-semibold hover:transform hover:-translate-y-0.5 hover:shadow-lg hover:shadow-blue-600/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none" 
                                id="${addToCartBtnId}" onclick="EcommerceCartModal.addVariantToCart()" disabled>
                            <i class="fas fa-cart-plus mr-2"></i>Add to Cart
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        currentModal = document.getElementById(modalId);
        
        // Store data on the modal element to avoid global variables
        currentModal.ecomData = {
            variants: data.variants,
            colors: data.colors,
            sizes: data.sizes,
            priceId,
            colorErrorId,
            sizeErrorId,
            stockInfoId,
            quantityInputId,
            decreaseBtnId,
            increaseBtnId,
            addToCartBtnId
        };

        // Show modal with animation
        setTimeout(() => {
            currentModal.classList.remove('opacity-0');
            currentModal.classList.add('opacity-100');
            currentModal.querySelector('.bg-gray-900').classList.remove('scale-95');
            currentModal.querySelector('.bg-gray-900').classList.add('scale-100');
        }, 10);

        // Close on overlay click
        currentModal.addEventListener('click', (e) => {
            if (e.target === currentModal) {
                closeModal();
            }
        });

        // ESC key handler - isolated to this modal
        escKeyHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        };
        document.addEventListener('keydown', escKeyHandler);
    }
    
    function closeModal() {
        if (currentModal) {
            currentModal.classList.add('opacity-0');
            currentModal.querySelector('.bg-gray-900').classList.add('scale-95');
            setTimeout(() => {
                currentModal.remove();
                currentModal = null;
            }, 300);
            
            // Remove isolated event listener
            if (escKeyHandler) {
                document.removeEventListener('keydown', escKeyHandler);
                escKeyHandler = null;
            }
        }
    }
    
    function selectColor(colorId) {
        selectedColor = colorId;
        
        // Update UI with scoped selectors
        if (currentModal) {
            currentModal.querySelectorAll('[data-ecom-color-id]').forEach(opt => {
                opt.classList.remove('ring-4', 'ring-blue-400', 'ring-offset-2', 'ring-offset-gray-900', 'border-blue-400');
                opt.classList.add('border-gray-600');
            });
            
            const selectedColorElement = currentModal.querySelector(`[data-ecom-color-id="${colorId}"]`);
            if (selectedColorElement) {
                selectedColorElement.classList.remove('border-gray-600');
                selectedColorElement.classList.add('ring-4', 'ring-blue-400', 'ring-offset-2', 'ring-offset-gray-900', 'border-blue-400');
            }
            
            // Hide error
            const colorError = document.getElementById(currentModal.ecomData.colorErrorId);
            if (colorError) {
                colorError.classList.add('hidden');
                colorError.classList.remove('flex');
            }
        }
        
        updateVariantSelection();
    }
    
    function selectSize(sizeId) {
        selectedSize = sizeId;
        
        // Update UI with scoped selectors
        if (currentModal) {
            currentModal.querySelectorAll('[data-ecom-size-id]').forEach(opt => {
                opt.classList.remove('bg-blue-600', 'border-blue-500', 'shadow-lg', 'shadow-blue-600/25', 'transform', '-translate-y-1');
                opt.classList.add('bg-gray-800', 'border-gray-600');
            });
            
            const selectedSizeElement = currentModal.querySelector(`[data-ecom-size-id="${sizeId}"]`);
            if (selectedSizeElement) {
                selectedSizeElement.classList.remove('bg-gray-800', 'border-gray-600');
                selectedSizeElement.classList.add('bg-blue-600', 'border-blue-500', 'shadow-lg', 'shadow-blue-600/25', 'transform', '-translate-y-1');
            }
            
            // Hide error
            const sizeError = document.getElementById(currentModal.ecomData.sizeErrorId);
            if (sizeError) {
                sizeError.classList.add('hidden');
                sizeError.classList.remove('flex');
            }
        }
        
        updateVariantSelection();
    }
    
    function updateVariantSelection() {
        if (!currentModal || !currentModal.ecomData) return;
        
        const data = currentModal.ecomData;
        
        if (!selectedColor || !selectedSize) {
            selectedVariant = null;
            availableStock = 0;
            const stockInfo = document.getElementById(data.stockInfoId);
            if (stockInfo) {
                stockInfo.textContent = 'Select options to see availability';
                stockInfo.className = 'text-gray-400 font-medium';
            }
            const addBtn = document.getElementById(data.addToCartBtnId);
            if (addBtn) addBtn.disabled = true;
            return;
        }

        // Find matching variant
        const variant = data.variants.find(v => 
            v.color_id === selectedColor && v.size_id === selectedSize
        );

        if (variant) {
            selectedVariant = variant;
            availableStock = variant.stock;
            
            // Update price
            const priceElement = document.getElementById(data.priceId);
            if (priceElement) {
                priceElement.textContent = `₹${variant.price}`;
            }
            
            // Update stock info
            const stockInfo = document.getElementById(data.stockInfoId);
            const addBtn = document.getElementById(data.addToCartBtnId);
            
            if (stockInfo && addBtn) {
                if (availableStock > 0) {
                    stockInfo.textContent = `${availableStock} in stock`;
                    stockInfo.className = 'text-green-400 font-medium';
                    addBtn.disabled = false;
                } else {
                    stockInfo.textContent = 'Out of stock';
                    stockInfo.className = 'text-red-400 font-medium';
                    addBtn.disabled = true;
                }
            }
            
            // Update quantity controls
            updateQuantityControls();
        } else {
            selectedVariant = null;
            availableStock = 0;
            const stockInfo = document.getElementById(data.stockInfoId);
            const addBtn = document.getElementById(data.addToCartBtnId);
            
            if (stockInfo) {
                stockInfo.textContent = 'Combination not available';
                stockInfo.className = 'text-red-400 font-medium';
            }
            if (addBtn) addBtn.disabled = true;
        }
    }
    
    function updateQuantityControls() {
        if (!currentModal || !currentModal.ecomData) return;
        
        const data = currentModal.ecomData;
        const decreaseBtn = document.getElementById(data.decreaseBtnId);
        const increaseBtn = document.getElementById(data.increaseBtnId);
        
        if (decreaseBtn) decreaseBtn.disabled = currentQuantity <= 1;
        if (increaseBtn) increaseBtn.disabled = currentQuantity >= availableStock;
    }
    
    function decreaseQuantity() {
        if (currentQuantity > 1) {
            currentQuantity--;
            const quantityInput = document.getElementById(currentModal.ecomData.quantityInputId);
            if (quantityInput) quantityInput.value = currentQuantity;
            updateQuantityControls();
        }
    }
    
    function increaseQuantity() {
        if (currentQuantity < availableStock) {
            currentQuantity++;
            const quantityInput = document.getElementById(currentModal.ecomData.quantityInputId);
            if (quantityInput) quantityInput.value = currentQuantity;
            updateQuantityControls();
        }
    }
    
    function updateQuantity(value) {
        const qty = parseInt(value) || 1;
        currentQuantity = Math.max(1, Math.min(qty, availableStock));
        const quantityInput = document.getElementById(currentModal.ecomData.quantityInputId);
        if (quantityInput) quantityInput.value = currentQuantity;
        updateQuantityControls();
    }
    
    async function addVariantToCart() {
        if (!currentModal || !currentModal.ecomData) return;
        
        const data = currentModal.ecomData;
        
        // Validate selection
        let hasError = false;
        
        if (data.colors && data.colors.length > 0 && !selectedColor) {
            const colorError = document.getElementById(data.colorErrorId);
            if (colorError) {
                colorError.classList.remove('hidden');
                colorError.classList.add('flex');
            }
            hasError = true;
        }
        
        if (data.sizes && data.sizes.length > 0 && !selectedSize) {
            const sizeError = document.getElementById(data.sizeErrorId);
            if (sizeError) {
                sizeError.classList.remove('hidden');
                sizeError.classList.add('flex');
            }
            hasError = true;
        }
        
        if (hasError) return;
        
        if (!selectedVariant) {
            showToast('error', 'Error', 'Please select valid options');
            return;
        }

        try {
            // Show loading state
            const addBtn = document.getElementById(data.addToCartBtnId);
            if (!addBtn) return;
            
            const originalContent = addBtn.innerHTML;
            addBtn.innerHTML = '<div class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>Adding...';
            addBtn.disabled = true;
            currentModal.classList.add('pointer-events-none', 'opacity-75');

            const csrftoken = getCookie('csrftoken');
            const response = await fetch('/cart/cart/add-variant/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    product_id: currentProduct.id,
                    variant_id: selectedVariant.id,
                    quantity: currentQuantity
                })
            });

            const responseData = await response.json();

            if (responseData.success) {
                closeModal();
                showToast('success', 'Added to Cart!', responseData.message);
                updateCartUI(responseData.cart);
            } else {
                showToast('error', 'Error', responseData.message);
                // Restore button
                addBtn.innerHTML = originalContent;
                addBtn.disabled = false;
                currentModal.classList.remove('pointer-events-none', 'opacity-75');
            }
        } catch (error) {
            console.error('EcommerceCartModal Error:', error);
            showToast('error', 'Network Error', 'Failed to add to cart. Please try again.');
            
            // Restore button
            const addBtn = document.getElementById(data.addToCartBtnId);
            if (addBtn) {
                addBtn.innerHTML = '<i class="fas fa-cart-plus mr-2"></i>Add to Cart';
                addBtn.disabled = false;
            }
            if (currentModal) {
                currentModal.classList.remove('pointer-events-none', 'opacity-75');
            }
        }
    }
    
    function updateCartUI(cartData) {
        console.log('EcommerceCartModal: Cart updated:', cartData);
        
        // Update cart badge/counter if exists
        const cartBadge = document.querySelector('.cart-badge');
        if (cartBadge) {
            cartBadge.textContent = cartData.items_count || 0;
        }
        
        // Dispatch custom event for other parts of your app to listen to
        document.dispatchEvent(new CustomEvent('ecommerceCartUpdated', {
            detail: cartData
        }));
    }
    
    // Main function to add product to cart
    async function fillProductIntoCart(productId) {
        try {
            showToast('success', 'Loading...', 'Adding product to cart...', 2000);
            
            const csrftoken = getCookie('csrftoken');
            const response = await fetch(`/cart/cart/fill-product/${productId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                }
            });

            const data = await response.json();

            if (data.success) {
                if (data.requires_variant_selection) {
                    // Show variant selection modal
                    showVariantModal(data);
                } else {
                    // Product added directly
                    showToast('success', 'Product added to cart!', data.message);
                    updateCartUI(data.cart);
                }
            } else {
                showToast('error', 'Error', data.message);
            }
        } catch (error) {
            console.error('EcommerceCartModal Error:', error);
            showToast('error', 'Network Error', 'Failed to add product to cart. Please try again.');
        }
    }
    
    // Public API
    return {
        fillProductIntoCart: fillProductIntoCart,
        closeModal: closeModal,
        selectColor: selectColor,
        selectSize: selectSize,
        decreaseQuantity: decreaseQuantity,
        increaseQuantity: increaseQuantity,
        updateQuantity: updateQuantity,
        addVariantToCart: addVariantToCart,
        removeToast: removeToast,
        
        // Utility method to check if modal is open
        isModalOpen: function() {
            return currentModal !== null;
        },
        
        // Method to programmatically open modal with data
        openModal: function(productData) {
            if (productData && productData.requires_variant_selection) {
                showVariantModal(productData);
            }
        }
    };
})();

// Optional: Add CSS to prevent conflicts
(function() {
    const style = document.createElement('style');
    style.textContent = `
        .ecom-modal * {
            box-sizing: border-box;
        }
        .ecom-toast-container {
            pointer-events: none;
        }
        .ecom-toast {
            pointer-events: auto;
        }
        .ecom-color-option:focus {
            outline: none;
        }
        .ecom-size-option:focus {
            outline: 2px solid #3b82f6;
            outline-offset: 2px;
        }
    `;
    document.head.appendChild(style);
})();