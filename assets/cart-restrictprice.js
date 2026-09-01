
  document.addEventListener('DOMContentLoaded', function () {
    const MIN_TOTAL = 500;
    const checkoutButton = document.getElementById('checkout');
    const noticeContainer = document.querySelector('.noticed_p');

    // Get numeric total from .totals__total-value
    function getCartTotal() {
      const totalEl = document.querySelector('.totals__total-value');
      if (!totalEl) return 0;

      const totalText = totalEl.textContent.replace(/[^0-9.]/g, '');
      return parseFloat(totalText) || 0;
    }

    // Update the checkout button state
    function updateCheckoutButtonState() {
			if(!checkoutButton)return;
			
      const cartTotal = getCartTotal();

      // Remove existing warning
      const existingMsg = document.querySelector('.min-total-msg');
      if (existingMsg) existingMsg.remove();

      if (cartTotal < MIN_TOTAL) {
        // ✅ Add exact disabled="disabled"
        checkoutButton.setAttribute('disabled', 'disabled');
        checkoutButton.style.opacity = "0.5";
        checkoutButton.style.cursor = "not-allowed";

        if (noticeContainer) {
          const msg = document.createElement('p');
          msg.className = 'min-total-msg';
          msg.style.color = 'red';
          msg.style.fontSize = '14px';
          msg.style.textAlign = 'right';
          msg.textContent = "🛒Minimum order value is $500. Please add more items to proceed.";
          noticeContainer.appendChild(msg);
          noticeContainer.style.display = 'block';
        }

      } else {
        // ✅ Remove exact disabled="disabled"
        checkoutButton.removeAttribute('disabled');
        checkoutButton.style.opacity = "1";
        checkoutButton.style.cursor = "pointer";

        if (noticeContainer) {
          noticeContainer.style.display = 'none';
        }
      }
    }

    // Initial state check
    updateCheckoutButtonState();

    // Watch cart total DOM updates (if dynamic)
    const totalNode = document.querySelector('.totals__total-value');
    if (totalNode) {
      const observer = new MutationObserver(() => {
        updateCheckoutButtonState();
      });
      observer.observe(totalNode, { childList: true, characterData: true, subtree: true });
    }

    // Handle clicks on quantity +/− buttons
    const qtyButtons = document.querySelectorAll('.quantity__button');
    qtyButtons.forEach(button => {
      button.addEventListener('click', () => {
        setTimeout(updateCheckoutButtonState, 600); // Adjust delay as needed
      });
    });

    // Handle manual input changes
    const qtyInputs = document.querySelectorAll('input[name^="updates["]');
    qtyInputs.forEach(input => {
      input.addEventListener('change', () => {
        setTimeout(updateCheckoutButtonState, 300);
      });
    });
  });
