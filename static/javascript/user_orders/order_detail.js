// Ensure DOM is loaded before defining functions
document.addEventListener('DOMContentLoaded', function() {
    
    // Define functions in global scope
    window.cancelOrder = function() {
        document.getElementById('cancelModal').classList.remove('hidden');
    }

    window.closeCancelModal = function() {
        document.getElementById('cancelModal').classList.add('hidden');
    }

    // Event listener for cancel confirmation
    const cancelConfirmBtn = document.getElementById('cancelConfirm');
    if (cancelConfirmBtn) {
        cancelConfirmBtn.addEventListener('click', function() {
            fetch(`/user_orders/${ORDER_ID}/cancel/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.message || 'Failed to cancel order');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to cancel order');
            })
            .finally(() => {
                closeCancelModal();
            });
        });
    }

    // Get CSRF token function
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
});

// Alternative approach - define functions globally without DOMContentLoaded
// Use this if you need the functions available immediately

/*
function cancelOrder() {
    document.getElementById('cancelModal').classList.remove('hidden');
}

function closeCancelModal() {
    document.getElementById('cancelModal').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', function() {
    const cancelConfirmBtn = document.getElementById('cancelConfirm');
    if (cancelConfirmBtn) {
        cancelConfirmBtn.addEventListener('click', function() {
            // ... rest of the code same as above
        });
    }
});
*/

