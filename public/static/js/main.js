/**
 * LabFix Main Application JS
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSidebar();
  initAnimatedCounters();
  initDropdowns();
});

/* Theme Toggle */
function initTheme() {
  const currentTheme = localStorage.getItem('labfix-theme') || 'light';
  document.documentElement.setAttribute('data-theme', currentTheme);

  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  if (themeToggleBtn) {
    updateThemeIcon(themeToggleBtn, currentTheme);
    themeToggleBtn.addEventListener('click', () => {
      const activeTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('labfix-theme', newTheme);
      updateThemeIcon(themeToggleBtn, newTheme);
    });
  }
}

function updateThemeIcon(btn, theme) {
  if (theme === 'dark') {
    btn.innerHTML = `<i class="fa-solid fa-sun"></i>`;
    btn.title = "Switch to Light Mode";
  } else {
    btn.innerHTML = `<i class="fa-solid fa-moon"></i>`;
    btn.title = "Switch to Dark Mode";
  }
}

/* Sidebar Toggle (Mobile & Desktop) */
function initSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
  
  if (sidebar && sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 992) {
        if (!sidebar.contains(e.target) && !sidebarToggleBtn.contains(e.target) && sidebar.classList.contains('mobile-open')) {
          sidebar.classList.remove('mobile-open');
        }
      }
    });
  }
}

/* Animated Statistics Counter */
function initAnimatedCounters() {
  const counters = document.querySelectorAll('.animate-counter');
  counters.forEach(counter => {
    const target = parseInt(counter.getAttribute('data-target') || counter.innerText, 10);
    if (isNaN(target)) return;

    let current = 0;
    const duration = 1200;
    const stepTime = Math.max(Math.floor(duration / (target || 1)), 20);

    counter.innerText = '0';
    const timer = setInterval(() => {
      current += Math.ceil(target / 40) || 1;
      if (current >= target) {
        counter.innerText = target;
        clearInterval(timer);
      } else {
        counter.innerText = current;
      }
    }, stepTime);
  });
}

/* Dropdowns */
function initDropdowns() {
  const dropdownWrappers = document.querySelectorAll('.dropdown-wrapper');
  dropdownWrappers.forEach(wrapper => {
    const toggle = wrapper.querySelector('.dropdown-toggle');
    if (toggle) {
      toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        // Close other dropdowns
        dropdownWrappers.forEach(w => {
          if (w !== wrapper) w.classList.remove('open');
        });
        wrapper.classList.toggle('open');
      });
    }
  });

  // Close when clicking anywhere outside
  document.addEventListener('click', () => {
    dropdownWrappers.forEach(w => w.classList.remove('open'));
  });
}

/* Toast Notifications */
function showToast(title, message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const iconMap = {
    success: 'fa-circle-check text-success',
    danger: 'fa-circle-exclamation text-danger',
    warning: 'fa-triangle-exclamation text-warning',
    info: 'fa-circle-info text-primary'
  };

  const iconClass = iconMap[type] || iconMap.info;

  toast.innerHTML = `
    <i class="fa-solid ${iconClass}" style="font-size: 1.25rem; margin-top: 2px;"></i>
    <div style="flex: 1;">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
  `;

  container.appendChild(toast);

  // Auto remove after 4.5 seconds
  setTimeout(() => {
    toast.style.transition = 'all 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(15px)';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

/* Modal Helper */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}
