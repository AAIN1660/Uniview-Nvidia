import React, { useEffect, useState } from "react";
import "./CategoryModal.scss";
import "./UserForm.scss";
import Button from "react-bootstrap/Button";
import { trackPromise } from "react-promise-tracker";
import categoryService from "../api/categoryService";
import Alert from "react-bootstrap/Alert";
import Form from "react-bootstrap/Form";
import dbConnectionService from "../api/dbConnectionService";
import LoadingOverlay from "../../src/components/LoadingOverlay/LoadingOverlay"

function CategoryModal({ closeModal, modalHeader, setCategory, category, getCategoryList, categoryList, onEdit }) {
    const [database, setDatabase] = useState([]);
    const [selectedDB, setSelectedDB] = useState("");
    const [showErrorMsg, setShowErrorMsg] = useState(false);
    const [sanityErrorMsg, setSanityErrorMsg] = useState("");
    const [tableNames, setTableNames] = useState([]);
    const [databaseId, setDatabaseId] = useState("");
    const [searchDB, setSearchDB] = useState(""); // Search term for database dropdown
    const [searchTable, setSearchTable] = useState(""); // Search term for table names
    const [selectedOptions, setSelectedOptions] = useState(category?.tables_list || []);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("")



    const validator = () => {
        if (!category.category_name) {
            setShowErrorMsg(true);
            setSanityErrorMsg("Category name is required");
            return false;
        }
        if (!category.category_code) {
            setShowErrorMsg(true);
            setSanityErrorMsg("Category code is required");
            return false;
        }
        setShowErrorMsg(false);
        return true;
    };

    const handleSubmit = (e) => {
         // Show loader
        const email = localStorage.getItem("email");
    
        e.preventDefault();
    
        if (validator()) {
            try {
                
    
                if (!category.id) {

                    setLoading(true);
                    setMessage("Adding Categories")
                    let params = {
                        category_name: category.category_name,
                        category_code: category.category_code,
                        db_connection_id: databaseId,
                        tables_list: selectedOptions,
                        email: email,
                    };
                   
                        categoryService
                            .addCategory(params)
                            .then((res) => {
                                closeModal();
                                alert(res.data.message);
                                getCategoryList();
                            })
                            .catch((err) => {
                                console.log(err);
                                alert("Error adding category");
                            })
                            .finally(() => setLoading(false)) // Hide loader after success/error
                    
                } else {
                    setLoading(true);
                    setMessage("Updating  Categories")
                    let params = {
                        category_id: category.id,
                        category_name: category.category_name,
                        category_code: category.category_code,
                        db_connection_id: databaseId,
                        tables_list: selectedOptions,
                        status_flag: category.status,
                    };
                   
    
                    trackPromise(
                        categoryService
                            .updateCategory(params)
                            .then((res) => {
                                closeModal();
                                // alert(res.data.message);
                                alert("Category Updated Successfully")
                                getCategoryList();
                            })
                            .catch((err) => {
                                console.log(err);
                                alert("Error updating category");
                            })
                            .finally(() => setLoading(false)) // Hide loader after success/error
                    );
                }
            } catch (error) {
                console.log("Error while submitting:", error);
                setLoading(false); // Hide loader in case of synchronous error
            }
        } else {
            setLoading(false); // Hide loader if validation fails
        }
    };
    

    const getDatabase = () => {
        dbConnectionService.getDBConnections().then((response) => {
            setDatabase(response.data.db_conn_data);
        });
    };

    const handleDatabaseChange = (dbName, id) => {

        setSelectedDB(dbName);
        console.log('====================================');
        console.log(databaseName);
        console.log('====================================');
        setSelectedOptions([]);
        setDatabaseId(id);
        dbConnectionService
            .getdatadictionary(id)
            .then((res) => {
                setTableNames(res.data.db_dictionary_data);
            })
            .catch((err) => {
                alert("Error");
            });
    };



    const handleCheckboxChange = (tableName) => {
        if (selectedOptions.includes(tableName)) {
            setSelectedOptions(selectedOptions.filter((option) => option !== tableName));
        } else {
            setSelectedOptions([...selectedOptions, tableName]);
        }
    };

    console.log('====================================');
    console.log(selectedOptions);
    console.log('====================================');

    console.log('====================================');
    console.log(databaseId);
    console.log('====================================');

    useEffect(() => {
        getDatabase();
    }, []);

    // Integration to show selected database and table names when editing
    useEffect(() => {

        if (category?.db_connection_id) {
            // Fetch the tables when a database is already selected
            dbConnectionService
                .getdatadictionary(category.db_connection_id)
                .then((res) => {
                    setTableNames(res.data.db_dictionary_data);

                    // Ensure the tables_list is correctly populated for pre-selection
                    const tableNamesInCategory = res.data.db_dictionary_data.map((table) => table.table_name);
                    setCategory((prev) => ({
                        ...prev,
                        tables_list: prev.tables_list.filter((table) => tableNamesInCategory.includes(table)),
                    }));
                })
                .catch((err) => {
                    console.log("Error fetching table names", err);
                    alert("Error fetching table names");
                });
        }
    }, [category.db_connection_id]);

    const getDatabaseNameById = (id) => {
        const dbEntry = database.find(db => db.id === id);
        return dbEntry ? dbEntry.db_name : null; // Return db_name or null if not found
    };
    const databaseName = getDatabaseNameById(category.db_connection_id);
    console.log('====================================');
    console.log(databaseName);
    console.log('====================================');

    // Filtered options for the search functionality
    const filteredDatabases = database.filter((db) =>
        db.db_name.toLowerCase().includes(searchDB.toLowerCase())
    );
    const filteredTableNames = tableNames.filter((table) =>
        table.table_name.toLowerCase().includes(searchTable.toLowerCase())
    );

    useEffect(() => {
        // alert("onedit")

        if (onEdit === 'Edit') {

            console.log('====================================');
            console.log(category.db_connection_id);
            console.log('====================================');
            console.log(databaseName);
            console.log('====================================');
            console.log('====================================');
            getTablesNamesONEdit(category.db_connection_id, databaseName)
        }



    }, [onEdit])

    const getTablesNamesONEdit = (id, dbName) => {

        console.log('====================================');
        console.log(id);
        console.log('====================================');
        setSelectedDB(dbName);
        // setSelectedOptions([]);
        setDatabaseId(id);
        dbConnectionService
            .getdatadictionary(id)
            .then((res) => {
                setTableNames(res.data.db_dictionary_data);
            })
            .catch((err) => {
                alert("Error");
            });
    }

    console.log('====================================');
    console.log(selectedDB);
    console.log('====================================');



    return (
        <>
            {loading && <LoadingOverlay message={message} />}

            <div>

                <div className="categoryModal">
                    <div className="container h-100">
                        <div>
                            <div className="d-inline add-dataset-title">
                                {modalHeader}
                                <i className="fa fa-times float-right" style={{ color: "#222" }} onClick={closeModal}></i>
                            </div>
                            <div
                                className="col-auto pad-l-0 mt-2"
                                style={{ backgroundColor: "#EEECF2", padding: "16px", borderRadius: "5px" }}
                            >
                                <div className="categorysection">
                                    {showErrorMsg && (
                                        <Alert
                                            variant="danger"
                                            onClose={() => {
                                                setShowErrorMsg(false);
                                                setSanityErrorMsg("");
                                            }}
                                            dismissible
                                        >
                                            <Alert.displayName>{sanityErrorMsg}</Alert.displayName>
                                        </Alert>
                                    )}

                                    <div className="row">
                                        {/* Category Name and Code */}
                                        <div>
                                            <label>Category Name</label>
                                            <input
                                                type="text"
                                                name="category"
                                                className="form-control shadow-none"
                                                placeholder="Category Name"
                                                value={category?.category_name}
                                                onChange={(e) => {
                                                    setCategory({ ...category, category_name: e.target.value });
                                                    setShowErrorMsg(false);
                                                    setSanityErrorMsg("");
                                                }}
                                            />
                                        </div>
                                        <div>
                                            <label>Category Code</label>
                                            <input
                                                type="text"
                                                name="category"
                                                className="form-control shadow-none"
                                                placeholder="Category Code"
                                                value={category?.category_code || ""}
                                                onChange={(e) => {
                                                    setCategory({ ...category, category_code: e.target.value });
                                                    setShowErrorMsg(false);
                                                    setSanityErrorMsg("");
                                                }}
                                            />
                                        </div>

                                        {/* Database Dropdown with Search */}
                                        {/* <div>
                                            <label>Database</label>
                                            <div className="dropdown">
                                                <button
                                                    className="btn drop form-control dropdown-toggle"
                                                    type="button"
                                                    id="dropdownMenuButton"
                                                    data-bs-toggle="dropdown"
                                                    aria-expanded="false"
                                                >

                                                    {selectedDB || (category.db_connection_id || category.databaseId ? databaseName : "select a Database")}


                                                </button>
                                                <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton" style={{ width: "100%" }}>
                                                    <li>
                                                        <input
                                                            type="text"
                                                            className="form-control"
                                                            placeholder="Search database..."
                                                            value={searchDB}
                                                            onChange={(e) => setSearchDB(e.target.value)}
                                                        />
                                                    </li>
                                                    {filteredDatabases.map((db) => (
                                                        <li key={db.id}>
                                                            <button
                                                                className="dropdown-item"
                                                                onClick={() => handleDatabaseChange(db.db_name, db.id)}
                                                            >
                                                                {db.db_name}
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        </div> */}

                                        {/* Table Names Multi-select Dropdown with Search */}
                                        {/* {(selectedDB || databaseName) && (
                                            <div className="mt-3">
                                                <label>Table Names</label>
                                                <div className="dropdown">
                                                    <button
                                                        className="btn btn-outline-primary form-control dropdown-toggle categorybutton"
                                                        type="button"
                                                        id="multiSelectDropdown"
                                                        data-bs-toggle="dropdown"
                                                        aria-expanded="false"
                                                    >
                                                        {selectedOptions.length > 0
                                                            ? selectedOptions.join(", ")
                                                            : "Select Options"}
                                                    </button>
                                                    <ul
                                                        className="dropdown-menu"
                                                        aria-labelledby="multiSelectDropdown"
                                                        style={{
                                                            maxHeight: "200px",
                                                            overflowY: "auto",
                                                            width: "295px",
                                                        }}
                                                    >
                                                        
                                                        <li>
                                                            <input
                                                                type="text"
                                                                className="form-control"
                                                                placeholder="Search tables..."
                                                                value={searchTable}
                                                                onChange={(e) => setSearchTable(e.target.value)}
                                                            />
                                                        </li>

                                                      
                                                        <li>
                                                            <div className="form-check">
                                                                <input
                                                                    className="form-check-input check-style"
                                                                    type="checkbox"
                                                                    id="selectAll"
                                                                    checked={selectedOptions.length === tableNames.length}
                                                                    onChange={(e) => {
                                                                        if (e.target.checked) {
                                                                            setSelectedOptions(tableNames.map((table) => table.table_name));
                                                                        } else {
                                                                            setSelectedOptions([]);
                                                                        }
                                                                    }}
                                                                />
                                                                <label className="form-check-label" htmlFor="selectAll">
                                                                    Select All
                                                                </label>
                                                            </div>
                                                        </li>

                                                       
                                                        {filteredTableNames.map((table) => (
                                                            <li key={table.id}>
                                                                <div className="form-check">
                                                                    <input
                                                                        className="form-check-input check-style"
                                                                        type="checkbox"
                                                                        id={`table-${table.id}`}
                                                                        value={table.table_name}
                                                                        checked={selectedOptions.includes(table.table_name)}
                                                                        onChange={() => handleCheckboxChange(table.table_name)}
                                                                    />
                                                                    <label
                                                                        className="form-check-label"
                                                                        htmlFor={`table-${table.id}`}
                                                                        style={{ width: "193px" }}
                                                                    >
                                                                        {table.table_name}
                                                                    </label>
                                                                </div>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </div>
                                        )} */}

                                    </div>
                                </div>
                            </div>
                        </div>
                        <Form>
                            <div className="mt-4">
                                <div className="d-flex flex-row-reverse">
                                    <Button
                                        className="mt-2 cancel-btn btn-sm"
                                        variant="primary"
                                        onClick={closeModal}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        className="mt-2 create-btn btn-sm"
                                        variant="primary"
                                        onClick={handleSubmit}
                                    >
                                        Submit
                                    </Button>
                                </div>
                            </div>
                        </Form>
                    </div>
                </div>
            </div>
        </>
    );
}

export default CategoryModal;
