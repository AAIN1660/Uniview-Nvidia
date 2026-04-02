/**
 * owner : retrAIver
 * author : Manish from Affine
 */
//import api from "./interceptor";
import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

class dbConnectionService {
    createDBConnection({host,  username, password, db_name}) {
    const data = {
        host: host,
        username: username,
        password: password,
        db_name: db_name
    };
    return api
      .post("/dbConnectionRouter/db_conn",data)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      });
  }

  getDBConnections() {
    return api
      .get("/dbConnectionRouter/get_db_conn_creds")
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      });
  }
  getdatadictionary(payload) {
    return api
      .get(`/dbConnectionRouter/get_data_dictionary?db_connection_id=${payload}`)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      }); 
  }

  updateDataDictionary(selectedTable) {
    console.log(selectedTable)
    const data = {
      id: selectedTable.id,
      db_connection_id: selectedTable.db_connection_id,
      table_desc: selectedTable.table_desc,
      table_name: selectedTable.table_name,
      columns: selectedTable.columns
  };
    return api
      .put("/dbConnectionRouter/update_data_dictionary",selectedTable)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      });
  }

  getSampleData(id) {
    const data = {
      id: id,
  };
    return api
      .get(`/dbConnectionRouter/get_sample_data?id=${id}`)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        throw err;
      });
  }
  
  get_user_tables(email) {
    return api
    .get(`/dbConnectionRouter/get_user_tables?email=${email}`)
    .then((response) => {
      return response;
    })
    .catch((err) => {
      throw err;
    });
  }
  
}

export default new dbConnectionService();
