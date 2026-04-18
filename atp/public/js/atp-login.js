/* ATP Login Page — branding patches
   Guards with a pathname check so this is safe to include
   globally via web_include_js. */
(function () {
  if (window.location.pathname !== '/login') return;

  function applyBranding() {
    /* 1. Inject ATP logo badge above each login/forgot form head */
    document.querySelectorAll(
      '.for-login .page-card-head, .for-email-login .page-card-head, .for-forgot .page-card-head'
    ).forEach(function (head) {
      if (head.querySelector('.atp-login-logo')) return;
      var badge = document.createElement('div');
      badge.className = 'atp-login-logo';
      badge.innerHTML = '<span>ATP</span>';
      head.insertBefore(badge, head.firstChild);
    });

    /* 2. Rename titles */
    var titleMap = {
      '.for-login .page-card-head h4': 'Sign in to ATP',
      '.for-email-login .page-card-head h4': 'Sign in to ATP',
      '.for-forgot .page-card-head h4': 'Reset your password',
    };
    Object.keys(titleMap).forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) el.textContent = titleMap[sel];
    });

    /* 3. Add ATP contact line after the login button */
    document.querySelectorAll('.for-login .page-card-actions, .for-email-login .page-card-actions').forEach(function (actions) {
      if (actions.parentNode.querySelector('.atp-contact-message')) return;
      var msg = document.createElement('div');
      msg.className = 'atp-contact-message';
      msg.textContent = 'Need access? Contact your instructor.';
      actions.parentNode.insertBefore(msg, actions.nextSibling);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBranding);
  } else {
    applyBranding();
  }
})();
