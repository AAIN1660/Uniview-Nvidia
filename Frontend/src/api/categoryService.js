//import api from "./interceptor";
import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

class categoryService {
  getCategory(payload) {
    let querybuilder = `?status_flag=0`
    if(payload.type ==="user"){
      querybuilder = `?status_flag=1&email=${payload.email}`;
    }
    else if(payload.type === 'active') {
      querybuilder = `?status_flag=1`
    } else {
      querybuilder = `?status_flag=0`
    }
    
    // console.log(`/documentService/getCategories/${querybuilder}`,"querybuilder")
    return api
      .get(`/documentService/getCategories${querybuilder}`)
      .then((res) => {
        return res;
      })
      .catch((err) => {});
  }

  updateCategory(payload) {
    // let queryBuilder = "";
    // if (payload.category_name) {
    //   queryBuilder = queryBuilder + `&category_name=${payload.category_name}`;
    // }
    // if (payload.category_code) {
    //   queryBuilder = queryBuilder + `&category_code=${payload.category_code}`;
    // }
    // if (payload.db_connection_id) {
    //   queryBuilder = queryBuilder + `&db_connection_id=${payload.db_connection_id}`;
    // }
    // if (payload.tables_list) {
    //   queryBuilder = queryBuilder + `&tables_list=${payload.tables_list}`;
    // }
    // if (queryBuilder === "") {
    //   if (payload.status_flag === 0) {
    //     payload.status_flag = false;
    //   } else {
    //     payload.status_flag = true;
    //   }
    //   queryBuilder = queryBuilder + `status_flag=${payload.status_flag}`;
    // }
    // if(payload.status_flag) {
    //   
    //   queryBuilder = queryBuilder + `&status_flag=${payload.status_flag}`;
    // }
    // console.log( `/documentService/updateCategory?category_id=${payload.category_id}&${queryBuilder}`)
    return api
      .put(
        "/documentService/updateCategory",payload
      )
      .then((res) => {
        return res;
        
      })
      .catch((err) => {
        console.log(err);
        alert(err.response.data.message);
      });
  }
  addCategory(payload) {
    // alert("hello")

    return api
      .post(
        "/documentService/addCategory",payload
      )
      .then((res) => {
        return res;
      })
      .catch((err) => {
        alert(err.response.data.message);
      });
  }
}

export default new categoryService();
