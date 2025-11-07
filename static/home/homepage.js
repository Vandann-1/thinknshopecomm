 let mobileMenuOpen = false;

        function toggleMobileMenu() {
            const mobileMenu = document.querySelector('.mobile-menu');
            mobileMenuOpen = !mobileMenuOpen;
            
            if (mobileMenuOpen) {
                mobileMenu.classList.add('open');
                document.body.style.overflow = 'hidden';
            } else {
                mobileMenu.classList.remove('open');
                document.body.style.overflow = '';
            }
        }

        function showSearchSuggestions() {
            // This function can be expanded to show dynamic search suggestions
            console.log('Search suggestions shown');
        }

        function previousBanner() {
            // Cycle through promotional banners
            console.log('Previous banner');
        }

        function nextBanner() {
            // Cycle through promotional banners
            console.log('Next banner');
        }

        // Hide search suggestions when clicking outside
        document.addEventListener('click', function(event) {
            const searchContainer = document.querySelector('.search-container');
            const searchSuggestions = document.querySelector('.search-suggestions');
            
            if (!searchContainer.contains(event.target)) {
                searchSuggestions.style.opacity = '0';
                searchSuggestions.style.visibility = 'hidden';
                searchSuggestions.style.transform = 'translateY(-10px)';
            }
        });

        // Close mobile menu on escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && mobileMenuOpen) {
                toggleMobileMenu();
            }
        });

        // Add scroll effect to navigation
        window.addEventListener('scroll', function() {
            const nav = document.querySelector('nav');
            if (window.scrollY > 0) {
                nav.style.backgroundColor = 'rgba(17, 24, 39, 0.98)';
            } else {
                nav.style.backgroundColor = 'rgba(31, 41, 55, 0.95)';
            }
        });




// HERO SECTION ===============================================================================================================================

   // Countdown Timer
        function updateCountdown() {
            const saleEndDate = new Date().getTime() + (7 * 24 * 60 * 60 * 1000); // 7 days from now
            const now = new Date().getTime();
            const distance = saleEndDate - now;

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            document.getElementById('days').textContent = days.toString().padStart(2, '0');
            document.getElementById('hours').textContent = hours.toString().padStart(2, '0');
            document.getElementById('minutes').textContent = minutes.toString().padStart(2, '0');
            document.getElementById('seconds').textContent = seconds.toString().padStart(2, '0');
        }

        // Update countdown every second
        setInterval(updateCountdown, 1000);
        updateCountdown(); // Initial call

        // Wishlist functionality
        function toggleWishlist(button) {
            const heart = button.querySelector('.heart');
            if (button.classList.contains('active')) {
                button.classList.remove('active');
                heart.textContent = '♡';
            } else {
                button.classList.add('active');
                heart.textContent = '♥';
            }
        }

        // Filter products
        function filterProducts(category) {
            const products = document.querySelectorAll('.product-card');
            const filterButtons = document.querySelectorAll('.filter-btn');
            
            // Update active button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            // Filter products with animation
            products.forEach(product => {
                product.style.transform = 'scale(0.8)';
                product.style.opacity = '0';
                
                setTimeout(() => {
                    if (category === 'all' || product.dataset.category === category) {
                        product.style.display = 'block';
                        product.style.transform = 'scale(1)';
                        product.style.opacity = '1';
                    } else {
                        product.style.display = 'none';
                    }
                }, 200);
            });
        }

        // Quick View functionality
        function quickView(productName) {
            alert(`Quick view for: ${productName}\n\nThis would open a product modal in a real application.`);
        }

        // Loading overlay
        function showLoading() {
            const overlay = document.getElementById('loadingOverlay');
            overlay.classList.add('active');
            
            setTimeout(() => {
                overlay.classList.remove('active');
                alert('Shop Now clicked! This would redirect to the shop page.');
            }, 2000);
        }

        // Smooth scrolling for internal links
        document.addEventListener('DOMContentLoaded', function() {
            // Add parallax effect to hero section
            window.addEventListener('scroll', function() {
                const scrolled = window.pageYOffset;
                const hero = document.querySelector('.hero-gradient');
                if (hero) {
                    hero.style.transform = `translateY(${scrolled * 0.5}px)`;
                }
            });

            // Add intersection observer for product cards
            const observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            };

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.animation = 'slideInUp 0.6s ease-out forwards';
                    }
                });
            }, observerOptions);

            document.querySelectorAll('.product-card').forEach(card => {
                observer.observe(card);
            });
        });

        // Add click animations to buttons
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON') {
                const ripple = document.createElement('span');
                ripple.classList.add('ripple');
                ripple.style.left = e.offsetX + 'px';
                ripple.style.top = e.offsetY + 'px';
                e.target.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            }
        });