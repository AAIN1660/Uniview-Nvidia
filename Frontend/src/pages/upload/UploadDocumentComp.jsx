/**
 * owner : retrAIver
 * author : Manish from Affine
 */
import React, { useState } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import datasetService from "../../api/documentService";
import successIcon from "../../assets/images/success_icon.svg";
import { trackPromise } from "react-promise-tracker";
import "./UploadDocumentComp.scss";
import infoIcon from "../../assets/images/info_icon.svg";
import infoData from "../../assets/data/info.json";
import { Tooltip } from "bootstrap/dist/js/bootstrap.esm.min";
import Alert from "react-bootstrap/Alert";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import useCredit from "../../api/userCredit";
// import helper from "../services/tokenStore";

function UploadDocumentComp(componentprops) {
  const { categoryList } = componentprops
  const [fileName, setFileName] = useState([]);
  const [file, setFile] = useState([]);
  const [remarks, setRemarks] = useState("");
  const [sanityErrorMsg,] = useState("");
  const [show, setShow] = useState(false);
  const [invalidFileList, setInvalidFileList] = useState([]);
  const [loading, setLoading] = useState(false);
  const { creditBalance, setCreditBalance } = useCredit();
  const [vectorRagChecked, setVectorRagChecked] = useState(true);
  const [graphRagChecked, setGraphRagChecked] = useState(false);

  const email = localStorage.getItem('email');

  const getInitialCategory = () => {
    if (categoryList.length > 0) {
      return categoryList[0].id;
    } else {
      return 0;
    }
  }

  const [selectedCategory, setselectedCategory] = useState(getInitialCategory());
  // const {setCreditBalance} = useCredit()

  var tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new Tooltip(tooltipTriggerEl);
  });



  const changeRemarks = (e) => {
    setRemarks(e.target.value);
    // formValidation(e.target.value)
  };

  const onFileChange = (e) => {
    e.preventDefault();
    let fileNames = [];
    let files = [];
    let invalidFileListTemp = [];
    Array.from(e.target.files).forEach((ele) => {
      if (fileName.filter((existingFile) => existingFile === ele.name).length === 0) {
        if (
          ele.name.includes(".txt") ||
          ele.name.includes(".doc") ||
          ele.name.includes(".docx") ||
          ele.name.includes(".pdf") ||
          ele.name.includes(".csv") ||
          ele.name.includes(".xlsx") || 
          ele.name.includes(".jpg") || 
          ele.name.includes(".png") || 
          ele.name.includes(".jpeg")
        ) {
          fileNames.push(ele.name);
          files.push(ele);
        } else {
          fileNames.push(ele.name);
          invalidFileListTemp.push(ele.name);
        }
      }
    });
    setInvalidFileList(invalidFileListTemp);
    setFileName(fileNamesExisting => [...fileNamesExisting, ...fileNames]);
    setFile(filesExistingfiles => [...filesExistingfiles, ...files]);
    document.getElementById('pdf-file').value = "";
  };
  const removeFile = (deletedFile) => {
    let existingFileName = fileName.filter((filename) => filename !== deletedFile);
    setFileName(existingFileName);
    let existingFile = file.filter((eachfile) => eachfile?.name !== deletedFile);
    setFile(existingFile);
  }

  const clearState = () => {
    componentprops.clearState();
    componentprops.getAllDocuments();
  };

  const uploadDocumentDetails = () => {
    if (creditBalance <= 0) {
      alert('Insufficient balance. Please recharge your account.');
      return;
    }
    else {
      if (invalidFileList && invalidFileList.length) {
        let invalidFileStr = invalidFileList.join(",");
        alert(
          `Please upload only .txt, .doc, .docx, .jpg, .jpeg, .png or .pdf files.\nFollowing file/files have invalid format : ${invalidFileStr} `
        );
      } else {
        if (selectedCategory === 0) {
          alert("Select Category");
          return;
        }
        setLoading(true);
        trackPromise(
          datasetService.uploadFiles(email, file, remarks, selectedCategory, vectorRagChecked, graphRagChecked).then((response) => {
            if (response?.data?.message) {
              if (response?.data?.filename) {
                if (response?.data?.status == "success") {
                  alert(
                    `${response.data.filename} - ` + `${response.data.message}`
                  );
                } else {
                  alert(
                    `${response.data.filename} - ` + `${response.data.message}`
                  );
                }
              } else {
                alert(`${response.data.message}`);
              }
            }
            setLoading(false);
            clearState();
          }).catch(err => {
            setLoading(false);
            alert(err.response.data.message || "Something went wrong")
          })
        );
      }

    }

  };

  const handleCategory = (e) => {
    setselectedCategory(e.target.value)
  }
  return (
    <div>
      <div className="uploaddocsoverlay" style={{ right: componentprops.rightoffset }}>
        {show && (
          <Alert variant="danger" onClose={() => setShow(false)} dismissible>
            <Alert.Heading>Sanity Check Error!</Alert.Heading>
            <p>{sanityErrorMsg}</p>
          </Alert>
        )}
        <i onClick={() => clearState()} class="fa fa-times crossicon" aria-hidden="true"></i>
        <div className="d-inline uploaddoctitle">Upload Document</div>
        {loading && <LoadingOverlay message="Uploading files..." />}
        <div className="col-auto pad-l-0 mt-2" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100% - 9vh)' }}>
          <div style={{ flex: 1 }}>
            <div>
              <form>
                <div className="flex-row">


                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <i style={{ fontSize: '48px', marginRight: '16px' }} className="fa-solid fa-file"></i>
                    <div style={{ width: '100%' }}>
                      <label style={{ fontSize: '0.8rem', margin: 5, fontWeight: 'lighter' }} className="upload-text mt-2">Category</label>
                      <select
                        className="form-control  mb-3 shadow-none inputfield"
                        onChange={handleCategory}
                        style={{ width: '100%' }}
                      >
                        {componentprops.categoryList.map((val) => (
                          <option selected={val.id == selectedCategory} key={val.category_name} value={val.id}>{val.category_name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                  <p className="upload-text">
                    RAG Type
                  </p>
                  <Form>
                  <div key={`inline-checkbox`} className="mb-3">
                  <Form.Check
                    inline
                    label="Vector RAG"
                    name="group1"
                    type='checkbox'
                    id={`inline-checkbox-2`}
                    checked={vectorRagChecked}
                    onChange={() => setVectorRagChecked(!vectorRagChecked)}
                  />
                  <Form.Check
                    inline
                    label="Graph RAG"
                    name="group2"
                    type='checkbox'
                    id={`inline-checkbox-1`}
                    checked={graphRagChecked}
                    onChange={() => setGraphRagChecked(!graphRagChecked)}
                  />
                  </div>
                  </Form>

                  </div>

                  <div className="upload-item mt-3">

                    <p className="upload-text">
                      Upload a File
                      <img
                        src={infoIcon}
                        className="info-icon-style cursor-pointer"
                        alt="Upload"
                        title={infoData.addDataset.fileupload}
                        data-bs-toggle="tooltip"
                        data-bs-placement="top"
                      />
                    </p>
                    {
                      <p className="choosetext">
                        {" "}
                        Maximum file size: 10 MB{" "}
                      </p>
                    }

                    {fileName && (
                      <div className="file-detail">
                        <span className="file-name">
                          {
                            fileName.map((eachFile) => <label style={{ margin: '5px', padding: '5px', backgroundColor: 'lightgray', borderRadius: '10px', marginRight: '10px' }}>{eachFile}<i onClick={() => removeFile(eachFile)} style={{ marginLeft: '5px', color: 'red' }} className="fa-solid fa-square-minus"></i></label>)
                          }
                        </span>
                      </div>
                    )}

                    <label
                      className="custom-file-upload btn btn-outline-secondary w-100 btn-sm"
                      title="Browse for a file."
                    >
                      Browse
                      <input
                        className="upload-cls inputfield"
                        type="file"
                        id="pdf-file"
                        accept=".doc, .docx,.pdf,.txt, .csv,.xlsx, .jpg, .jpeg, .png"
                        name="pdf-file"
                        onChange={onFileChange}
                        hidden
                        multiple
                      />
                    </label>
                    <div className="col-12 col-md-12 p-15">

                    </div>
                    <label className="upload-text mt-3">Remarks</label>
                    <textarea
                      className="form-control shadow-none inputfield"
                      rows="1"
                      onChange={changeRemarks}
                    ></textarea>
                  </div>
                </div>
              </form>
            </div>
          </div>

          <Form>
            <div className="mt-4">
              <div className="d-flex flex-row-reverse" style={{ justifyContent: 'start' }}>
                <Button
                  className="mt-2 btn-sm cancel-btn"
                  variant="primary"
                  onClick={clearState}
                >
                  {" "}
                  Cancel{" "}
                </Button>
                <Button
                  className="mt-2 btn-sm create-btn"
                  variant="primary"
                  onClick={uploadDocumentDetails}
                  disabled={file.length === 0}
                >
                  {" "}
                  {loading ? "Uploading..." : "Upload"}{" "}
                </Button>
              </div>
            </div>
          </Form>
        </div>

      </div>
    </div>
  );
}

export default UploadDocumentComp;
