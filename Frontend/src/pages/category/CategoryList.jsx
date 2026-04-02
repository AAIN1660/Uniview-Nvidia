import React, { useState, useEffect, useMemo } from "react";
import { useTable, usePagination, useGlobalFilter } from "react-table";
import Card from "react-bootstrap/Card";
import Button from "react-bootstrap/Button";
import { Checkbox, Panel, DefaultButton } from "@fluentui/react";
import CategoryModal from "../../modals/CategoryModal";

import categoryService from "../../api/categoryService";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import "./CategoryList.scss";

const CategoryList = ({tabId}) => {
  const [openModal, setOpenModal] = useState(false);
  const [modalHeader, setModalHeader] = useState("Add Category");
  const [categoryList, setCategoryList] = useState([]);
  const [filteredCategoryList, setFilteredCategoryList] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [category, setCategory] = useState({});
  const [loading, setLoading] = useState(true);
  const [onEdit, setonEdit] = useState("")
  const [loadingMessage, setLoadingMessage] = useState("fetching Categories")
  // Handle opening the modal
  const handleOpen = () => setOpenModal(true);
  const handleClose = () => setOpenModal(false);

  // Fetch the categories list
  useEffect(() => {
    getCategoryList();
  }, [tabId === "categories"]);

  let categoryListLoaded = false;

  // Get the category list from the backend API
  const getCategoryList = () => {
    if (categoryListLoaded) return; // Prevent multiple calls
    categoryListLoaded = true;
    setLoading(true);
    categoryService.getCategory({ type: "all" }).then((res) => {
      const fetchedCategoryList = res?.data?.CategoryList || [];
      fetchedCategoryList.forEach((val) => {
        const status_val = val.status;
        val.status = status_val === 1
          ? <span className="badge active-status">Active</span>
          : <span className="badge bg-danger">Inactive</span>;

        // Adding the action buttons (Edit, Activate/Deactivate)
        val.action = status_val === 0
          ? (
            <div>
              <i
                className="fa fa-solid fa-pencil"
                style={{ "color": "black" }}
                title="Edit Category"
                onClick={() => updateCategory(val,0)}
              ></i>
              <i
                className="ms-3 fa fa-solid fa-toggle-off text-danger"
                title="Activate Category"
                onClick={() => changeUserStatus(val.id, 1)}
              ></i>
            </div>
          )
          : (
            <div>
              <i
                className="fa fa-pencil"
                style={{ "color": "black" }}
                title="Edit Category"
                onClick={() => updateCategory(val,1)}
              ></i>
              <i
                className="ms-3 fa fa-solid fa-toggle-on text-success"
                title="Deactivate Category"
                onClick={() => changeUserStatus(val.id, 0)}
              ></i>
            </div>
          );
      });
      setCategoryList(fetchedCategoryList);
      setFilteredCategoryList(fetchedCategoryList);
      setLoading(false);
    });
  };

  // Handle category update (edit functionality)
  const updateCategory = (row,status) => {
    
    setonEdit("Edit")
    setModalHeader("Edit Category");
    console.log(category);
    
    setCategory({ ...category, id: row.id, category_name: row.category_name, category_code: row.category_code, db_connection_id:row.db_connection_id, tables_list:row.tables_list, status:status});
    handleOpen();
  };

  // Handle changing the category status (Activate/Deactivate)
  const changeUserStatus = (categoryID, status) => {
    
    const confirmAction = status === 1
      ? window.confirm("Are you sure you want to activate this category?")
      : window.confirm("Are you sure you want to deactivate this category?");


    if (confirmAction) {
      setLoadingMessage("Updating User Status")
      setLoading(true);
      categoryService.updateCategory({ category_id: categoryID, status_flag: status })
        .then((response) => {
          alert(response.data.message);
          getCategoryList(); // Refresh category list
          setLoading(false);
        });
    }
  };

  // Handle search functionality
  const handleSearch = (e) => {
    setSearchText(e.target.value);
    setGlobalFilter(e.target.value || undefined);
  };

  // React-Table hooks
  const data = useMemo(() => filteredCategoryList, [filteredCategoryList]);

  const columns = useMemo(() => [
    {
      Header: "Sl No",
      accessor: "id"
    },
    {
      Header: "Name",
      accessor: "category_name"
    },
    {
      Header: "Code",
      accessor: "category_code"
    },
    {
      Header: "Status",
      accessor: "status"
    },
    {
      Header: "Action",
      accessor: "action"
    }
  ], []);

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
      data,
      initialState: { pageIndex: 0, pageSize: 10 },
    },
    useGlobalFilter,
    usePagination
  );



  return (
    <>
      {loading && <LoadingOverlay message="Fetching categories..." />}

      {/* Modal for editing categories */}
      {openModal &&
        <CategoryModal closeModal={handleClose} modalHeader={modalHeader} setCategory={setCategory} category={category} getCategoryList={getCategoryList} onEdit={onEdit}/>
      }

      {/* Table for displaying categories */}
      <div className="App">
        <div className="container-fluid">
          <div className="row">
            <div className="col-12" style={{ position: 'relative', width: '98%', marginLeft: '1%', marginRight: '1%',marginTop:"-31px" }}>
              <div className="mt-3 categoryheader">
                <div className="text1" style={{marginTop:"2px"}}>Category</div>
                <div className="serach-cls">
                  <input
                    type="text"
                    placeholder="Search Category"
                    value={searchText}
                    onChange={handleSearch}
                    className="form-control"
                  />
                </div>
                <div className="adddataset-btn-div">
                  <Button
                    className="adddataset-btn"
                    variant="primary"
                    onClick={() => {
                      setModalHeader("Add Category");
                      setCategory({ id: "", category_name: "", category_code: "" });
                      handleOpen();
                    }}
                  >
                    <i className="fa-solid fa-plus me-2" /> New Category
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className="row" style={{ marginTop: '1rem !important', width: '98%', marginLeft: '1%', marginRight: '1%', marginTop: '1%' }}>
            <div className="col-12">
              <table className="table" {...getTableProps()}>
                <thead>
                  {headerGroups.map(headerGroup => (
                    <tr {...headerGroup.getHeaderGroupProps()}>
                      {headerGroup.headers.map(column => (
                        <th {...column.getHeaderProps()}>{column.render("Header")}</th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody {...getTableBodyProps()}>
                  {page.map(row => {
                    prepareRow(row);
                    return (
                      <tr {...row.getRowProps()}>
                        {row.cells.map(cell => (
                          <td {...cell.getCellProps()}>{cell.render("Cell")}</td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Pagination Controls */}
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
          </div>
        </div>
      </div>
    </>
  );
};

export default CategoryList;
