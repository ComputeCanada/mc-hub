import axios from "axios";

const baseURL = process.env.VUE_APP_API_URL || "/api";
const axiosInstance = axios.create({ baseURL });
let sessionExpired = false;

axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (typeof error.response === "undefined") {
      if (!sessionExpired) {
        // A network error was detected in the API request. This is probably due to a CORS
        // error in the redirection to the identity provider's login portal.
        // Note: Other network problems, such as disconnects, may cause the same behaviour.
        sessionExpired = true;
        console.log(error);
        alert("Your session expired. Please refresh the page.");

        // Remove any page reload confirmation dialog
        window.onbeforeunload = (event) => {
          delete event["returnValue"];
        };

        location.reload();
      }
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
