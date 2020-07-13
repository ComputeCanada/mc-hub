import axios from "axios";

const baseURL = process.env.VUE_APP_API_URL || "/api";
export default axios.create({ baseURL });
