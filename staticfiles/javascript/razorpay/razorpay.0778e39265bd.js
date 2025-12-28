// Helper function to get CSRF token
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

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    const payButton = document.getElementById('rzp-button');
    
    if (!payButton) {
        console.error('Payment button not found');
        return;
    }

    // Check if Razorpay is loaded
    if (typeof Razorpay === 'undefined') {
        console.error('Razorpay SDK not loaded');
        alert('Payment system not available. Please refresh the page.');
        return;
    }

    payButton.onclick = function(e) {
        e.preventDefault();
        
        // Validate required parameters
        const keyId = "{{ razorpay_key_id }}";
        const amount = "{{ amount }}";
        const orderId = "{{ razorpay_order_id }}";
        
        if (!keyId || !amount || !orderId) {
            alert('Payment configuration incomplete. Please try again.');
            console.error('Missing required payment parameters');
            return;
        }

        var options = {
            "key": keyId,
            "amount": amount, // Amount in paise
            "currency": "{{ currency }}",
            "name": "Skatezo",
            "description": "Order {{ order.order_id }}",
            "order_id": orderId,
            "handler": function (response) {
                // Show processing indicator
                document.getElementById('payment-processing').style.display = 'block';
                document.getElementById('rzp-button').style.display = 'none';

                // Send payment verification request to backend
                fetch('/orders/verify-payment/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_signature: response.razorpay_signature
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = data.redirect_url;
                    } else {
                        alert('Payment verification failed: ' + data.error);
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Payment verification error:', error);
                    alert('Error processing payment: ' + error);
                    window.location.reload();
                });
            },
            "prefill": {
                "name": "{{ user_name }}",
                "email": "{{ request.user.email }}", // Fixed: Use request.user.email
                "contact": "{{ user_phone }}"
            },
            "theme": {
                "color": "#3399cc"
            },
            "modal": {
                "ondismiss": function() {
                    // Handle payment modal dismissal
                    console.log("Payment modal closed");
                    // Reset UI state
                    document.getElementById('payment-processing').style.display = 'none';
                    document.getElementById('rzp-button').style.display = 'inline-block';
                }
            }
        };

        try {
            var rzp = new Razorpay(options);
            rzp.open();
        } catch (error) {
            console.error('Error opening Razorpay:', error);
            alert('Payment system error. Please try again.');
        }
    };
});