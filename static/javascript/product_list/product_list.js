// wishlist.js - Robust wishlist functionality with beautiful popup
// wishlist.js - Robust wishlist functionality with beautiful popup

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize wishlist functionality
    initializeWishlist();
});

// Initialize wishlist system
function initializeWishlist() {
    createPopupStyles();
    
    // Make grabWishList globally available
    window.grabWishList = grabWishList;
    window.closeWishlistPopup = closeWishlistPopup;
    
    console.log('Wishlist system initialized');
}

// Create popup styles dynamically
function createPopupStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .wishlist-popup-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }
        
        .wishlist-popup-overlay.show {
            opacity: 1;
            visibility: visible;
        }
        
        .wishlist-popup {
            background: white;
            border-radius: 16px;
            padding: 0;
            max-width: 450px;
            width: 90%;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            transform: scale(0.9) translateY(20px);
            transition: all 0.3s ease;
            position: relative;
        }
        
        .wishlist-popup-overlay.show .wishlist-popup {
            transform: scale(1) translateY(0);
        }
        
        .wishlist-popup-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 24px;
            text-align: center;
            position: relative;
        }
        
        .wishlist-popup-icon {
            font-size: 48px;
            margin-bottom: 12px;
            animation: heartBeat 1.5s ease-in-out;
        }
        
        @keyframes heartBeat {
            0% { transform: scale(1); }
            25% { transform: scale(1.2); }
            50% { transform: scale(1); }
            75% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .wishlist-popup-title {
            font-size: 20px;
            font-weight: 600;
            margin: 0;
        }
        
        .wishlist-popup-message {
            font-size: 14px;
            opacity: 0.9;
            margin-top: 4px;
        }
        
        .wishlist-popup-body {
            padding: 24px;
        }
        
        .wishlist-product-card {
            display: flex;
            gap: 16px;
            margin-bottom: 20px;
        }
        
        .wishlist-product-image {
            width: 80px;
            height: 80px;
            border-radius: 12px;
            object-fit: cover;
            background: #f3f4f6;
        }
        
        .wishlist-product-details {
            flex: 1;
        }
        
        .wishlist-product-name {
            font-size: 16px;
            font-weight: 600;
            margin: 0 0 4px 0;
            color: #1f2937;
            line-height: 1.3;
        }
        
        .wishlist-product-brand {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 8px;
        }
        
        .wishlist-product-price {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .wishlist-price-current {
            font-size: 16px;
            font-weight: 700;
            color: #059669;
        }
        
        .wishlist-price-original {
            font-size: 14px;
            color: #9ca3af;
            text-decoration: line-through;
        }
        
        .wishlist-discount-badge {
            background: #fef3c7;
            color: #d97706;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
        }
        
        .wishlist-product-variant {
            font-size: 12px;
            color: #6b7280;
            margin-top: 4px;
        }
        
        .wishlist-popup-actions {
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }
        
        .wishlist-btn {
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
        }
        
        .wishlist-btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .wishlist-btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .wishlist-btn-secondary {
            background: #f3f4f6;
            color: #374151;
            border: 1px solid #e5e7eb;
        }
        
        .wishlist-btn-secondary:hover {
            background: #e5e7eb;
        }
        
        .wishlist-popup-close {
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        
        .wishlist-popup-close:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.1);
        }
        
        .wishlist-count-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            background: #ef4444;
            color: white;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 10px;
            min-width: 18px;
            text-align: center;
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .wishlist-popup {
                background: #1f2937;
                color: white;
            }
            
            .wishlist-product-name {
                color: white;
            }
            
            .wishlist-btn-secondary {
                background: #374151;
                color: #d1d5db;
                border-color: #4b5563;
            }
            
            .wishlist-btn-secondary:hover {
                background: #4b5563;
            }
        }
        
        /* Loading state */
        .wishlist-loading {
            pointer-events: none;
            opacity: 0.7;
        }
        
        .wishlist-loading::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            margin: -10px 0 0 -10px;
            border: 2px solid #ccc;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

// Global functions for onclick handlers
window.grabWishList = window.grabWishList || function() {
    console.warn('Wishlist system not yet initialized. Please wait...');
};

window.closeWishlistPopup = window.closeWishlistPopup || function() {
    console.warn('Wishlist system not yet initialized. Please wait...');
};

// Get CSRF token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}

// Main wishlist function
async function grabWishList(productId, variantId = null) {
    // Get the event from arguments or window.event for older browsers
    const currentEvent = arguments[2] || window.event;
    
    // Prevent multiple clicks
    const button = currentEvent ? currentEvent.target.closest('button') : null;
    if (button?.classList.contains('wishlist-loading')) return;
    
    // Add loading state
    if (button) {
        button.classList.add('wishlist-loading');
    }
    
    try {
        // Prepare form data
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', getCSRFToken());
        if (variantId) {
            formData.append('variant_id', variantId);
        }
        
        // Make AJAX request
        const response = await fetch(`/product/wishlist/grab/${productId}/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update button appearance
            updateWishlistButton(button, data.action, data.icon, data.color);
            
            // Update wishlist count in header/nav
            updateWishlistCount(data.wishlist_count);
            
            // Show beautiful popup
            showWishlistPopup(data);
            
        } else {
            showErrorMessage(data.message);
        }
        
    } catch (error) {
        console.error('Wishlist error:', error);
        showErrorMessage('Something went wrong. Please try again.');
    } finally {
        // Remove loading state
        if (button) {
            button.classList.remove('wishlist-loading');
        }
    }
}

// Update wishlist button appearance
function updateWishlistButton(button, action, icon, color) {
    if (!button) return;
    
    const iconElement = button.querySelector('i');
    if (iconElement) {
        iconElement.className = `${icon} ${color} transition-colors`;
        
        // Add animation
        iconElement.style.transform = 'scale(1.3)';
        setTimeout(() => {
            iconElement.style.transform = 'scale(1)';
        }, 200);
    }
    
    // Update title
    button.title = action === 'added' ? 'Remove from Wishlist' : 'Add to Wishlist';
}

// Update wishlist count badge
function updateWishlistCount(count) {
    const badges = document.querySelectorAll('.wishlist-count, [data-wishlist-count]');
    badges.forEach(badge => {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'block' : 'none';
    });
}

// Show beautiful popup
function showWishlistPopup(data) {
    // Remove existing popup
    const existingPopup = document.querySelector('.wishlist-popup-overlay');
    if (existingPopup) {
        existingPopup.remove();
    }
    
    const product = data.product;
    const isAdded = data.action === 'added';
    
    // Create popup HTML
    const popupHTML = `
        <div class="wishlist-popup-overlay" onclick="closeWishlistPopup(event)">
            <div class="wishlist-popup" onclick="event.stopPropagation()">
                <div class="wishlist-popup-header">
                    <button class="wishlist-popup-close" onclick="closeWishlistPopup()">&times;</button>
                    <div class="wishlist-popup-icon">
                        <i class="${data.icon} ${data.color}"></i>
                    </div>
                    <h3 class="wishlist-popup-title">${isAdded ? 'Added to Wishlist!' : 'Removed from Wishlist'}</h3>
                    <p class="wishlist-popup-message">${data.message}</p>
                </div>
                
                <div class="wishlist-popup-body">
                    <div class="wishlist-product-card">
                        <img src="${product.image_url}" alt="${product.name}" class="wishlist-product-image" onerror="this.src='/static/images/no-image.jpg'">
                        <div class="wishlist-product-details">
                            <h4 class="wishlist-product-name">${product.name}</h4>
                            ${product.brand ? `<p class="wishlist-product-brand">${product.brand}</p>` : ''}
                            <div class="wishlist-product-price">
                                <span class="wishlist-price-current">₹${product.effective_price}</span>
                                ${product.discounted_price ? `<span class="wishlist-price-original">₹${product.base_price}</span>` : ''}
                                ${product.discount_percent > 0 ? `<span class="wishlist-discount-badge">${product.discount_percent}% OFF</span>` : ''}
                            </div>
                            ${product.color || product.size ? `<p class="wishlist-product-variant">${[product.color, product.size].filter(Boolean).join(' • ')}</p>` : ''}
                        </div>
                    </div>
                    
                    <div class="wishlist-popup-actions">
                        ${isAdded ? `
                            <button class="wishlist-btn wishlist-btn-primary" onclick="window.location.href='/wishlist/'">
                                <i class="fas fa-heart"></i> View Wishlist
                            </button>
                            <button class="wishlist-btn wishlist-btn-secondary" onclick="closeWishlistPopup()">
                                Continue Shopping
                            </button>
                        ` : `
                            <button class="wishlist-btn wishlist-btn-primary" onclick="window.location.href='/products/'">
                                <i class="fas fa-shopping-bag"></i> Continue Shopping
                            </button>
                            <button class="wishlist-btn wishlist-btn-secondary" onclick="closeWishlistPopup()">
                                Close
                            </button>
                        `}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add popup to DOM
    document.body.insertAdjacentHTML('beforeend', popupHTML);
    const popup = document.querySelector('.wishlist-popup-overlay');
    
    // Show popup with animation
    setTimeout(() => {
        popup.classList.add('show');
    }, 10);
    
    // Auto close after 5 seconds
    setTimeout(() => {
        closeWishlistPopup();
    }, 5000);
}

// Close popup
function closeWishlistPopup(event) {
    if (event && event.target !== event.currentTarget) return;
    
    const popup = document.querySelector('.wishlist-popup-overlay');
    if (popup) {
        popup.classList.remove('show');
        setTimeout(() => {
            popup.remove();
        }, 300);
    }
}

// Show error message
function showErrorMessage(message) {
    // Create simple error toast
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ef4444;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add CSS animations for toast
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(toastStyles);

// Keyboard support
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeWishlistPopup();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { grabWishList, closeWishlistPopup };
}


// ====================================================================================================================================================================================

