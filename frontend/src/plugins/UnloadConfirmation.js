/**
 * The RefreshConfirmation plugin enables a component to require confirmation with a confirm dialog
 * when the user attempts to exit, refresh or navigate to another page.
 *
 * This is useful when an input field has been modified by the user and we don't want the user to lose
 * the data.
 */

const CONFIRMATION_MESSAGE = "Your changes will be lost. Do you want do continue?";

export default {
  install(vue, { router }) {
    let requiresConfirmation = false;

    // Native browser refresh or page unload
    window.onbeforeunload = event => {
      if (requiresConfirmation) {
        event.preventDefault();

        // message display only supported in IE, but returnValue must be set for Chrome
        event.returnValue = CONFIRMATION_MESSAGE;
      } else {
        delete event["returnValue"];
      }
    };

    // Vue router page navigations
    router.beforeEach((to, from, next) => {
      if (requiresConfirmation) {
        if (confirm(CONFIRMATION_MESSAGE)) {
          next();
        } else {
          next(false);
        }
      } else {
        next();
      }
    });


    router.afterEach(() => {
      requiresConfirmation = false;
    });

    /**
     * Enables the confirmation dialog on the next navigation or page unload.
     */
    vue.prototype.$enableUnloadConfirmation = () => {
      requiresConfirmation = true;
    };

    /**
     * Disables the confirmation dialog on the next navigation or page unload.
     */
    vue.prototype.$disableUnloadConfirmation = () => {
      requiresConfirmation = false;
    };
  }
};
