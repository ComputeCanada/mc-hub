import axios from "axios";

const baseURL = process.env.VUE_APP_API_URL || "/api";
const axiosInstance = axios.create({ baseURL });

axiosInstance.interceptors.response.use((response)=> {
    return response;
}, (error) => {
    if (error.response.status == 302) {
        // API request was redirected to single sign-on login page, therefore the session expired
        location.reload();
    } else {
        return Promise.reject(error);
    }
})

export default axiosInstance;
