/**
 * owner : retrAIver
 * author : Manish from Affine
 */
import React, { useState, useEffect } from "react";
import { useTable, usePagination, useGlobalFilter } from "react-table";
import { Button, Card, Modal } from "react-bootstrap";
import UploadDocumentComp from "./UploadDocumentComp";
import datasetService from "../../api/documentService";
import { trackPromise } from "react-promise-tracker";
import { DateTimeFormatter, getSizeinKB } from "../../utils";
import { Checkbox, Panel, DefaultButton, TextField, SpinButton, Dropdown } from "@fluentui/react";
import categoryService from "../../api/categoryService";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import useCredit from "../../api/userCredit";
import "./DocumentsList.scss";
import vectorRag from '../../../src/assets/vector_rag.ico';
import graphRag from '../../../src/assets/graph_rag.ico';


function DocumentsList() {
  const [showAddDataset, setShowAddDataset] = useState(false);
  const [loading, setLoading] = useState(true);
  const [datasetsList, setDatasetsList] = useState([]);
  const [filteredDatasetsList, setFilteredDatasetsList] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [categoryList, setcategoryList] = useState([]);
  const [show, setShow] = useState(false);
  const [modalText, setModalText] = useState("");
  const [loaderMessage, setLoaderMessage] = useState("Fetching uploaded files...");
  const [isDisabled, setDisabled] = useState(false);

  const { creditBalance, setCreditBalance } = useCredit();

  const handleClose = () => setShow(false);
  const handleShow = () => setShow(true);

  useEffect(() => {
    getCategory();
  }, []);

  useEffect(() => {
    if (categoryList.length > 0) {
      // getCategory();
      getAllDocuments();
    }
  }, [categoryList]);

  const getCategory = () => {
    setLoaderMessage("Fetching uploaded files...");
    setLoading(true);
    categoryService
      .getCategory({ email: localStorage.email, type: "user" })
      .then((res) => {
        setcategoryList(res.data.CategoryList);
        setLoading(false);
      })
      .catch((err) => {
        console.log(err);
        setLoading(false);
      });
  };


  const getAllDocuments = () => {
    setLoaderMessage("Fetching uploaded files...");
    setLoading(true);
    const user_info = { email: localStorage.getItem("email") };
    datasetService
      .getAllDocuments(user_info)
      .then((response) => {
        const temp = response.data.Files.reverse().map((dataset, index) => ({
          ...dataset,
          id: index + 1,
          category:
            categoryList.find((catg) => catg.id === dataset.category_id)
              ?.category_name || "Unknown",
          status: dataset.status ? "Indexed" : "Uploaded",
          action: (
            <div className="actionicons">
              <i
                className="fas fa-trash text-danger"
                title="Delete Document"
                onClick={() => deleteDocs(dataset.chunk_ids, dataset.file_name)}
              ></i>
            </div>
          ),
        }));
        const final_data = temp.filter((catg) => catg.category !== undefined);
        setDatasetsList(final_data);
        setFilteredDatasetsList(final_data);
        setCreditBalance(response.data.balance);
        setLoading(false);
      })
      .catch((err) => {
        alert(err.response?.data?.error || "Failed to fetch documents");
        setLoading(false);
      });
  };



  const clearState = (datasetName) => {
    setShowAddDataset(false);
    if (datasetName) {
      getAllDocuments();
    }
  };

  const filterResultsBySearch = (val) => {
    setSearchText(val);
    let lowerVal = val.toLowerCase();
    if (!lowerVal) {
      setFilteredDatasetsList(datasetsList);
    } else {
      const results = datasetsList.filter(
        (data) =>
          data.category.toLowerCase().includes(lowerVal) ||
          data.file_name.toLowerCase().includes(lowerVal) ||
          data.uploaded_by.toLowerCase().includes(lowerVal)
      );
      setFilteredDatasetsList(results);
    }
  };

  const deleteDocs = (chunk_ids, file_name) => {
    const correctedString = chunk_ids.replace(/[\[\]']/g, '');
    const chunkIds = correctedString.split(', ').map((id) => id.trim());

    const confirmDelete = window.confirm("Are you sure you want to delete these documents?");
    if (confirmDelete) {
      setLoaderMessage("Deleting file...");
      setLoading(true);
      trackPromise(
        datasetService
          .deleteDocument(chunkIds, file_name)
          .then((response) => {
            alert(response.data.message || "File deleted successfully");
            getAllDocuments(); // Ensure this is called after a successful deletion
          })
          .catch((err) => {
            alert(err.response?.data?.message || "Failed to delete file");
            setLoading(false);
          })
      );
    }
  };

  const downloadDocs = (file_name) => {
      setLoaderMessage("Downloading file...");
      setLoading(true);
   
      trackPromise(
        datasetService
          .downloadDocument(file_name)
          .then((blob) => {
            // Create a Blob URL
            const url = window.URL.createObjectURL(new Blob([blob]));
           
            // Create a temporary anchor element
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", file_name); // Set the file name for download
   
            // Append to the document body and trigger the download
            document.body.appendChild(link);
            link.click();
   
            // Clean up after the download
            link.remove();
            window.URL.revokeObjectURL(url);
   
            setLoaderMessage("");
            setLoading(false);
            console.log(`File ${file_name} downloaded successfully.`);
          })
          .catch((err) => {
            alert(err.response?.data?.message || "Failed to download file");
            setLoaderMessage("");
            setLoading(false);
          })
      );
    };
   

  const columns = React.useMemo(
    () => [
      { Header: "#", accessor: "id" },
      { Header: "File Name", accessor: "file_name" },
      {
        Header: "Uploaded On",
        accessor: "uploaded_at",
        Cell: ({ value }) => DateTimeFormatter(value),
      },
      { Header: "Uploaded By", accessor: "uploaded_by" },
      {
        Header: "Size",
        accessor: "file_size",
        Cell: ({ value }) => getSizeinKB(value),
      },
      { Header: "Category", accessor: "category" },

      // { Header: "Index Status", accessor: "status", },
      {
        Header: "Index Status",
        accessor: "status",
        Cell: ({ row }) => {
          console.log('row', row);
          const { status, graphrag_index_status, vector_rag, graph_rag } = row.original;
      
          return (
            <div className="icon-container-table">
              {vector_rag && status === 'Indexed' && (
                <img className="iconcls" title="VectorRAG Indexed" src={vectorRag} alt="Vector RAG Indexed" />
              )}
              {graph_rag && graphrag_index_status === 1 && (
                <img className="iconcls" title="GraphRAG Indexed" src={graphRag} alt="Graph RAG Indexed" />
              )}
              {vector_rag && status !== 'Indexed' && (
                <i className="fa fa-cloud-upload uploadiconcls" title="VectorRAG Uploaded" aria-hidden="true"></i>
              )}
              {graph_rag && graphrag_index_status !== 1 && (
                <i className="fa fa-cloud-upload uploadiconcls" title="GraphRAG Uploaded" aria-hidden="true"></i>
              )}
            </div>
          );
        },
      },
  
      {
        Header: "Action",
        Cell: ({ row }) => (
          <div>
            <i
              className="fas fa-trash action-icon"
              title="Delete"
              style={{ cursor: "pointer" }}
              onClick={() => deleteDocs(row.original.chunk_ids, row.original.file_name)}
            ></i>
            <i
              className="fas fa-download download-icon mr-2"
              title="Download"
              style={{ cursor: "pointer" }}
              onClick={() => downloadDocs(row.original.file_name)}
            ></i>
          </div>
        ),
      },
    ],
    []
  );

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
    setGlobalFilter,
    page,
    canPreviousPage,
    canNextPage,
    pageOptions,
    gotoPage,
    nextPage,
    previousPage,
    setPageSize,
    state: { pageIndex, pageSize },
  } = useTable(
    {
      columns,
      data: filteredDatasetsList,
      initialState: { pageIndex: 0 },
    },
    useGlobalFilter,
    usePagination
  );
  const _onRefreshClick = () => {
    getAllDocuments();
  };
  const _onButtonClick = () => {
    setShowAddDataset(true);
  };

  return (
    <div  className="documentList">
      {loading && <LoadingOverlay message={loaderMessage} />}
      {showAddDataset && (
        <UploadDocumentComp
          clearState={(datasetName) => clearState(datasetName)}
          getAllDocuments={() => getAllDocuments()}
          categoryList={categoryList.filter((category) => category.status === 1)}
        />
      )}
      <Modal
        show={show}
        onHide={handleClose}
        backdrop="static"
        keyboard={false}
      >
        <Modal.Header closeButton>
          <Modal.Title>License Validation Error</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Please connect at{" "}
          <a href="mailto:retreaiveractivation@affine.ai">
            Affine Admin
          </a>
        </Modal.Body>
      </Modal>
      <div className="row" style={{ width: '100%', marginLeft: '2%', marginRight: '1%' }}>
        <div className="">
          <div className="mt-2 documentheader">
            <div className="text1" style={{ marginTop: '0.2rem', marginLeft: '-3.2rem' }}>Documents</div>
            <div className="text1 serach-cls">
              <input
                type="text"
                className="form-control search-input"
                placeholder="Search Documents"
                value={searchText}
                onChange={(e) => {
                  filterResultsBySearch(e.target.value);
                  setGlobalFilter(e.target.value);
                }}
              />
            </div>
            <div className="adddataset-btn-div">
              <Button variant="primary" onClick={_onRefreshClick} className="adddataset-btn" hidden={isDisabled}>
                <i className="fa fa-refresh me-2" title="Refresh"></i>
                Refresh
              </Button>
              <Button variant="primary" onClick={_onButtonClick} hidden={isDisabled} className="adddataset-btn">
                <i
                  className="fa fa-upload me-2"
                  title="Upload File"
                ></i>
                Upload Files
              </Button>
            </div>
          </div>
        </div>
      </div>
      {/* <div className=" mt-3 documentheader">
        <div className="text1">Documents</div>
 
        <div className="col-4">
          <input
            type="text"
            className="form-control search-input"
            placeholder="Search Documents"
            value={searchText}
            onChange={(e) => {
              filterResultsBySearch(e.target.value);
              setGlobalFilter(e.target.value);
            }}
          />
        </div>
        <div className="adddataset-btn-div">
 
        </div>
        <Button variant="primary" onClick={getAllDocuments}>
          Refresh
        </Button>
        <Button variant="primary" onClick={() => setShowAddDataset(true)}>
          Upload Files
        </Button>
      </div> */}
      <table {...getTableProps()} className="table table-striped mt-2">
        <thead>
          {headerGroups.map((headerGroup) => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map((column) => (
                <th {...column.getHeaderProps()}>{column.render("Header")}</th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody {...getTableBodyProps()}>
          {page.map((row) => {
            prepareRow(row);
            return (
              <tr {...row.getRowProps()}>
                {row.cells.map((cell) => (
                  <td {...cell.getCellProps()}>{cell.render("Cell")}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="pagination">
        {/* First Page Button */}
        <button
          onClick={() => gotoPage(0)}
          disabled={!canPreviousPage}
          type="button"
          className="btn"
        >
          {"<<"}
        </button>

        {/* Previous Page Button */}
        <button
          onClick={() => previousPage()}
          disabled={!canPreviousPage}
          type="button"
          className="btn"
        >
          {"<"}
        </button>

        {/* Page Numbers */}
        {pageOptions.length > 1 &&
          pageOptions.map((_, index) => (
            <button
              key={index}
              onClick={() => gotoPage(index)}
              className={`btn ${pageIndex === index ? "active" : ""}`}
              type="button"
            >
              {index + 1}
            </button>
          ))}

        {/* Next Page Button */}
        <button
          onClick={() => nextPage()}
          disabled={!canNextPage}
          type="button"
          className="btn"
        >
          {">"}
        </button>

        {/* Last Page Button */}
        <button
          onClick={() => gotoPage(pageOptions.length - 1)}
          disabled={!canNextPage}
          type="button"
          className="btn"
        >
          {">>"}
        </button>
      </div>


    </div>
  );
}

export default DocumentsList; 