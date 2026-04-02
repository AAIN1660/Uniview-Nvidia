//import api from "./interceptor";
import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

class askService {

  askQuestion(payload) {
    //  alert("hello")
    
    return api
      .post(
        "/generate_response",payload
      )
      .then((res) => {
        return res;
      })
      .catch((err) => {
        alert(err.response.data.message);
      });
  }

  getQuestion(payload) {
    //  alert("hello")
    
    return api
      .post(
        "/userCreditService/user/questions",payload
      )
      .then((res) => {
        return res;
      })
      .catch((err) => {
        alert(err.response.data.message);
      });
  }

  questionFeedback(payload) {
    //  alert("hello")
    
    return api
      .put(
        "/questionFeedback",payload
      )
      .then((res) => {
        return res;
      })
      .catch((err) => {
        alert(err.response.data.message);
      });
  }
}

export default new askService();
