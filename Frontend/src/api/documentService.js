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

class documentService {
  uploadFiles(email, file, remarks, category_id, vectorRagChecked, graphRagChecked) {
    const payload = new FormData();
    payload.append("email", email);
    payload.append("remarks", remarks);
    payload.append("category_id", category_id);
    payload.append('vector_rag', vectorRagChecked);
    payload.append('graph_rag', graphRagChecked);

    file.forEach((ele, i) => {
      payload.append("files", ele);
    });
    const config = {
      headers: { "content-type": "multipart/form-data" },
    };
    return api.post(`/uploadManagementRouter/uploadFile`, payload, config).then((response) => {
      return response;
    })
    .catch((err) => {
      throw err;
    });;
  }

  getAllDocuments(user_info) {
    const querybuilder = `?email=${user_info.email}`;
    return api
      .get(`/uploadManagementRouter/uploadedFilesList${querybuilder}`)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        console.log(err)
        // return this.getAllDocuments()
      });
  }

  deleteDocument(chunk_ids,file_name) {
    const data = {
      chunk_ids:chunk_ids,
      blob_name: file_name
    };
    return api
      .post("/uploadManagementRouter/deleteFile",data)
      .then((response) => {
        return response;
      })
      .catch((err) => {
        console.log(err);
      });
  }
  
  getSharePointData(){
    return api
     .get(`/uploadManagementRouter/getSharePointData`)
     .then((response) => {
      return response;
    })
    .catch((err) => {
      console.log(err)
    });
   }

   downloadDocument(file_name) {
    const data = { blob_name: file_name };
 
    return api
      .post("/uploadManagementRouter/downloadFile", data, {
        responseType: "blob", // Ensure the response is handled as a binary file
      })
      .then((response) => {
        return response.data; // Return the Blob data
      })
      .catch((err) => {
        console.error("Error while downloading file:", err);
        throw err;
      });
  }
}

export default new documentService();
