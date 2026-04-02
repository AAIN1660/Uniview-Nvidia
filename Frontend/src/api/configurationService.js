/**
 * owner : UNified
 * author : Gourav from Affine
 */

import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

class configurationService {
    updateConfig(payload) {
    return api
      .put("/configManagementRouter/update_config",payload)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      });
  }

  getConfigurationDetails() {
    return api
      .get(`/configManagementRouter/get_config?id=${'configuration'}`)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      });
  }


  
  
}

export default new configurationService();
