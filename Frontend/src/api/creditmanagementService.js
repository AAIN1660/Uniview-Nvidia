/**
 * owner : retrAIver
 * author : Arpitha from Affine
 */
import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

class usercreditsService {
    userdata(userInfo) {
        return api
          .post("/userCreditService/user",userInfo)
          .then((response) => {
            return response;
          })
          .catch((err) => {
            console.log(err);
          });
      }

      creditdata(username){
        return api
        .get(`/userCreditService/get_user_balance?username=${username}`)
        .then((response) =>{
          return response
        })
        .catch((err) => {
          console.log(err);
        });
      }
      
      fetchUsers = () => {
        return api
        .get('/userCreditService/getusers')
        .then(response => {
          return response;
        })
        .catch((err) => {
          throw err;
        });
      }

      updateUsers = (user_info) => {
        return api
          .put("/userCreditService/updateroleandtransactions/",user_info)
          .then((response) => {
            return response;
          })
          .catch((err) => {
            throw err;
          });
      }

      addUser = (user_info) => {
        return api
          .post("/userCreditService/add_user_by_admin/",user_info)
          .then((response) => {
            return response;
          })
          .catch((err) => {
            throw err;
          }); 
      }

      usertransctiondetails  = (email) => {
        return api
        .get(`/userCreditService/transaction_details?email=${email}`)
        .then(response => {
          return response
        })
        .catch((err) => {
          console.log(err);
        });
      }

      updateuserstatus = ({status, email} ) => {
        return api
        .put(`/userCreditService/update_user_status`,{status,email})
        .then((reponse) => {
          console.log(reponse);
           return reponse
        })
        .catch((err) => {
          throw err;
        });
      }

}

export default new usercreditsService() 