/**
 * The UnloadConfirmation plugin enables a component to require confirmation with a confirm dialog
 * when the user attempts to exit, refresh or navigate to another page.
 *
 * This is useful when an input field has been modified by the user and we don't want the user to lose
 * the data.
 */

const CONFIRMATION_MESSAGE = "Your changes will be lost. Do you want to continue?";

export default {
  install(app, { router }) {
    let requiresConfirmation = false;
    const previousBeforeUnload = window.onbeforeunload;

    // Native browser refresh or page unload
    const beforeUnload = (event) => {
      if (requiresConfirmation) {
        event.preventDefault();

        // Browsers display their own message; returnValue supports older clients.
        event.returnValue = CONFIRMATION_MESSAGE;
      } else {
        delete event["returnValue"];
      }
    };
    // Repository.js replaces this property before a session-expiry reload.
    window.onbeforeunload = beforeUnload;

    // Vue router page navigations
    const removeBeforeGuard = router.beforeEach(() => !requiresConfirmation || window.confirm(CONFIRMATION_MESSAGE));

    const removeAfterGuard = router.afterEach((to, from, failure) => {
      if (!failure) requiresConfirmation = false;
    });

    /**
     * Enables the confirmation dialog on the next navigation or page unload.
     */
    app.config.globalProperties.$enableUnloadConfirmation = () => {
      requiresConfirmation = true;
    };

    /**
     * Disables the confirmation dialog on the next navigation or page unload.
     */
    app.config.globalProperties.$disableUnloadConfirmation = () => {
      requiresConfirmation = false;
    };

    app.onUnmount(() => {
      requiresConfirmation = false;
      removeBeforeGuard();
      removeAfterGuard();
      if (window.onbeforeunload === beforeUnload) window.onbeforeunload = previousBeforeUnload;
    });
  },
};
