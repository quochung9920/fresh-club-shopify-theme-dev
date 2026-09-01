  document.addEventListener('DOMContentLoaded', function () {
    const MAX_QTY = 10;

    // Show or remove the quantity warning message
function handleQuantityValidation(input) {
  const wrapper = input.closest('quantity-input');
  if (!wrapper) return;

  const qty = parseInt(input.value, 10) || 0;

  const errorContainer = document.querySelector('.cart-item__error');
  const errorText = errorContainer?.querySelector('.cart-item__error-text');

  const existingMsg = wrapper.querySelector('.qty-limit-msg');
  if (existingMsg) existingMsg.remove();

  if (qty > MAX_QTY) {
    input.value = MAX_QTY;

    // Inline warning
    const msg = document.createElement('p');
    msg.className = 'qty-limit-msg';
    msg.textContent = `⚠️ You cannot order more than ${MAX_QTY} of this item.`;
    msg.style.color = 'red';
    msg.style.fontSize = '13px';
    msg.style.marginTop = '6px';
    wrapper.appendChild(msg);

    // Show icon and message
    if (errorContainer && errorText) {
      errorText.textContent = `You cannot order more than ${MAX_QTY}.`;
      errorContainer.style.display = 'flex';
    }

    // 🔔 Show popup notification
    showQtyPopup(`Only ${MAX_QTY} items were added to your cart due to availability.`);
  } else {
    if (errorContainer && errorText) {
      errorText.textContent = '';
      errorContainer.style.display = 'none';
    }
  }
}

// ✅ Helper to show popup notification
function showQtyPopup(message) {
  const popup = document.getElementById('qty-popup-notification');
  if (!popup) return;

  popup.textContent = message;
  popup.style.display = 'block';

  // Hide after 3 seconds
  setTimeout(() => {
    popup.style.display = 'none';
  }, 3000);
}


    // Move cart-item__error-text below <quantity-input>
    function moveErrorTextBelowQuantity() {
      const quantityWrapper = document.querySelector('quantity-input');
      const errorMsg = document.querySelector('.cart-item__error-text');

      if (quantityWrapper && errorMsg) {
        quantityWrapper.insertAdjacentElement('afterend', errorMsg);
      }
    }

    // Quantity input
    const quantityInput = document.querySelector('quantity-input input[name="quantity"]');

    if (quantityInput) {
      // On manual input
      quantityInput.addEventListener('input', function () {
        handleQuantityValidation(quantityInput);
      });

      quantityInput.addEventListener('change', function () {
        handleQuantityValidation(quantityInput);
      });
    }

    // On "+" button click
    const plusBtn = document.querySelector('quantity-input .quantity__button[name="plus"]');
    if (plusBtn) {
      plusBtn.addEventListener('click', function () {
        setTimeout(() => {
          handleQuantityValidation(quantityInput);
        }, 100); // Wait for value to update
      });
    }

    // On "-" button click
    const minusBtn = document.querySelector('quantity-input .quantity__button[name="minus"]');
    if (minusBtn) {
      minusBtn.addEventListener('click', function () {
        setTimeout(() => {
          handleQuantityValidation(quantityInput);
        }, 100);
      });
    }

    // Move error message below quantity on load
    moveErrorTextBelowQuantity();
  });