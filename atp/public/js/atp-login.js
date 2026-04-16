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

    /* 3. Replace sign-up messages with the ATP contact line */
    document.querySelectorAll('.for-login .sign-up-message, .for-email-login .sign-up-message').forEach(function (el) {
      /* CSS already hides el — insert a sibling with the custom copy */
      if (el.parentNode.querySelector('.atp-contact-message')) return;
      var msg = document.createElement('div');
      msg.className = 'atp-contact-message';
      msg.textContent = 'Need access? Contact your instructor.';
      el.parentNode.insertBefore(msg, el);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBranding);
  } else {
    applyBranding();
  }
})();
