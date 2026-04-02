/**
 * owner : retrAIver
 * author : Arpitha from Affine
 */
import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

class userService {
  loginUser(userInfo) {
    return api
      .post("/userCreditService/login_custom", userInfo)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        console.log(err);
      });
  }
}

export default new userService();
