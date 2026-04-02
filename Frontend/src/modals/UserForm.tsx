import React, { useEffect, useState } from "react";
import axios from "axios";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import { trackPromise } from "react-promise-tracker";
import { MultiSelect } from "react-multi-select-component";

import usercreditsService from "../api/creditmanagementService";
import useCredit from "../api/userCredit";
import { User } from "../types";
import { roleTypes } from "../constants";
import LoadingOverlay from "../components/LoadingOverlay/LoadingOverlay";

import "./UserForm.scss";
import { ComboBox, IComboBoxOption } from "@fluentui/react";

import dbConnectionService from "../api/dbConnectionService";

const api = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL,
  headers: { "Content-Type": "application/json" },
});

interface UserFormProps {
  closeModal: () => void;
  modalHeader: string;
  userObj: User | null;
  fetchUsers: () => void;
  creditPoolBalance: number;
  useCreditPool: boolean;
  setCreditPoolBalance: () => void;
  allActiveCategories: any;
  mode: "add" | "update";
}

const UserForm: React.FC<UserFormProps> = ({
  userObj,
  modalHeader,
  closeModal,
  fetchUsers,
  useCreditPool,
  creditPoolBalance,
  setCreditPoolBalance,
  allAciveCategories,
  mode,
}) => {
  const [currentUser, setCurrentUser] = useState<User>(() => {
    if (mode === "update" && userObj) {
      return userObj;
    } else {
      return {
        email: "",
        username: "",
        role: "General",
        CreditAssigned: 0,
        categories: [],
        db_connection_id: "1",
        tables_list: [
            "Inventory",
            "Invoice_2",
            "Order",
            "shipping"
        ],
        password: "",
      };
    }
  });

  console.log("---------->")
  console.log(userObj);


  const [credits, setCredits] = useState<number>(0);
  const [error, setError] = useState(null);
  const [creditAction, setCreditAction] = useState("assign");
  const [enableUpdateUser, setEnableUpdateUser] = useState(false);
  const [submitButtonText, setSubmitButtonText] = useState(mode === "add" ? "Add" : "Update");
  const [loading, setLoading] = useState(false);
  const [loaderMessage, setLoaderMessage] = useState(mode === "add" ? "Creating User..." : "Updating User...");
  const dataloaderMessage = mode === "add" ? "Preparing form..." : "Fetching user details...";
  const [allCategories, setAllCategories] = useState(allAciveCategories);
  const originalUserCategories = userObj?.categories
  const [allUserCategories, setAllUserCategories] = useState([]);
  const [allTables, setAllTables] = useState([]);
  const [selectedTables, setSelectedTables] = useState([]);

  const { creditBalance, setCreditBalance } = useCredit();
  const login_email = localStorage.getItem('email');
  const [showPassword, setShowPassword] = useState
  (false);
  const [tableNames, setTableNames] = useState([]);
  const [database, setDatabase] = useState([]);

  const [alldatabase, setAllDatabases] = useState([]);



  const handleCancel = () => {
    closeModal();
  };

  const changeCreditAction = (event) => {
    setCreditAction(event.target.value);
  };


  // Validating credit assigning and revoking
  const validateCreditAction = () => {
    let enable = true;
    if (
      creditAction === "assign" &&
      useCreditPool &&
      credits > creditPoolBalance
    ) {
      setError(
        `Credits assigned exceeds credit pool balance ${creditPoolBalance}`
      );
      enable = false;
    }
    if (creditAction === "revoke" && credits > userObj?.balance) {
      setError("Not enough balance to revoke");
      enable = false;
    }
    return enable;
  };

  useEffect(() => {
  
    // Fetch the tables when a database is already selected
    dbConnectionService
        .getdatadictionary(currentUser?.db_connection_id)
        .then((res) => {

            // Ensure the tables_list is correctly populated for pre-selection
            const tableNamesInCategory = res.data.db_dictionary_data.map((table) => table.table_name);
            // setAllTables
            const updatedTables = tableNamesInCategory.map((table) => ({
              value: table,
              label: table,
            }))
  
          setAllTables(updatedTables)
        })
        .catch((err) => {
            console.log("Error fetching table names", err);
            alert("Error fetching table names");
        });

}, [currentUser]);


  // validating update user form
  useEffect(() => {
    if (credits < 0) {
      setError("Credits cannot be less than 0");
      setEnableUpdateUser(false);
    } else if (
      allCategories.length > 0 &&
      JSON.stringify(allUserCategories) !==
      JSON.stringify(originalUserCategories)
    ) {
      setEnableUpdateUser(true);
    } else if (credits == 0 && userObj?.role !== currentUser.role) {
      setEnableUpdateUser(true);
      setError("");
    } else if (credits == 0 && userObj?.role === currentUser.role) {
      setEnableUpdateUser(false);
    } else if (credits > 0) {
      if (validateCreditAction()) {
        setEnableUpdateUser(true);
        setError(" ");
      } else {
        setEnableUpdateUser(false);
      }
    }
  }, [currentUser, credits, creditAction, allUserCategories]);


  // Function to update selected tables when categories change
  const updateTables = () => {
    // if (selectedCategories.length === 0) {
    //   setSelectedTables([]);
    //   return;
    // }

    const updatedTables =  currentUser?.tables_list.map((table) => ({
      value: table,
      label: table,
    }))

  setSelectedTables(updatedTables);
};

useEffect(() => {
  updateTables();
}, [currentUser]);


  useEffect(() => {
    let userCategories = allCategories.filter(category => userObj?.categories.includes(category.value));
    setAllUserCategories(userCategories);

  }, [userObj?.categories])

  const createUser = () => {
    setSubmitButtonText("Adding...");
    const categoriesPayload = allUserCategories.map(cat => cat.value)
    setLoading(true);
    const isCategoriesUpdated =
      allCategories.length > 0 &&
      JSON.stringify(allUserCategories) !==
      JSON.stringify(originalUserCategories);
      console.log('database', database)
    const options = {

      email: currentUser.email,
      new_role: currentUser.role,
      categories: categoriesPayload,
      name: currentUser.username,
      password: currentUser.password,
      selecteddatabase: database.map(item => item.label),
      selectedtables: selectedTables.map(item => item.label)
    };

    if (creditAction === "assign") {
      options["CreditAssigned"] = Number(credits);
    } else {
      options["Credit_Revoked"] = Number(credits);
    }

    options["admin_email"] = login_email;
    const user_info = JSON.stringify(options);

    trackPromise(
      usercreditsService
        .addUser(user_info)
        .then((response) => {
          const { message } = response?.data;
          setSubmitButtonText("Add");
          fetchUsers();
          alert(message || `User created successfully`);
          setLoading(false);
          closeModal();
        })
        .catch((err) => {
          const { error } = err.response.data;
          setSubmitButtonText("Add");
          setError(error);
          setLoading(false);
          alert(error);
        })
    );
  };


  const updateUser = () => {
    setSubmitButtonText("Updating...");
    const categoriesPayload = allUserCategories.map(cat => cat.value)
    setLoading(true);
    const isCategoriesUpdated =
      allCategories.length > 0 &&
      JSON.stringify(allUserCategories) !==
      JSON.stringify(originalUserCategories);
      console.log('database', database)

    const options = {
      email: currentUser.email, // Include email field
      id: currentUser.id,
      new_role: currentUser.role,
      categories: categoriesPayload,
      password: currentUser.password,
      selecteddatabase: database.map(item => item.label),
      selectedtables: selectedTables.map(item => item.label)

    };

    if (creditAction === "assign") {
      options["CreditAssigned"] = Number(credits);
    } else {
      options["Credit_Revoked"] = Number(credits);
    }

    const user_info = JSON.stringify(options);
    trackPromise(
      usercreditsService
        .updateUsers(user_info)
        .then((response) => {
          const { email = "", balance, credit_pool_balance } = response?.data;
          setSubmitButtonText("Update");
          fetchUsers();
          if (email === localStorage.getItem("email")) {
            if (balance !== creditBalance) {
              setCreditBalance(balance);
            }
          }
          setCreditPoolBalance(credit_pool_balance);

          alert(
            response.data.message ||
            `User record updated successfully`
          );
          setLoading(false);
          closeModal();
        })
        .catch((err) => {
          const { error } = err.response.data;
          setSubmitButtonText("Update");
          setError(error);
          setLoading(false);
          alert(error);
        })
    );
  };

  const handleSubmit = () => {
    if (mode === "add") {
      createUser();
    } else {
      updateUser();
    }
  };

  const setUserRole = (e) => {
    setCurrentUser((prevUser) => ({
      ...prevUser,
      role: e.target.value,
    }));
  };


  const getDatabase = () => {
    dbConnectionService.getDBConnections().then((response) => {

      const listofDatabases =  response.data.db_conn_data.map((table) => ({
        value: table.db_name,
        label: table.db_name,
      }))
      
        setAllDatabases(listofDatabases)
        setDatabase(listofDatabases);
    });
};



const getDatabaseNameById = (id) => {
const dbEntry = database.find(db => db.id === id);
return dbEntry ? dbEntry.db_name : null; // Return db_name or null if not found
};

console.log(getDatabaseNameById('1'))

// Integration to show selected database and table names when editing
useEffect(() => {

    if (currentUser?.db_connection_id) {
      getDatabase()
        // Fetch the tables when a database is already selected
        dbConnectionService
            .getdatadictionary(currentUser.db_connection_id)
            .then((res) => {
                console.log(res.data.db_dictionary_data)
                setTableNames(res.data.db_dictionary_data);

                // Ensure the tables_list is correctly populated for pre-selection
                const databaseTableNames = res.data.db_dictionary_data.map((table) => table.table_name);
                
                // setCategory((prev) => ({
                //     ...prev,
                //     tables_list: prev.tables_list.filter((table) => tableNamesInCategory.includes(table)),
                // }));
            })
            .catch((err) => {
                console.log("Error fetching table names", err);
                alert("Error fetching table names");
            });
    }
}, [currentUser?.db_connection_id]);
  return (
    <div>
      <div className="overlay">
        {loading && <LoadingOverlay message={loaderMessage} />}
        <div className="container h-100 d-flex justify-content-center align-items-center section-view frame">
          <div className="pop-card-pos p-3 bg-white rounded shadow-lg datasetoverlayelm uploadStyle">
            <div className="d-flex flex-row justify-content-space-between align-items-center">
              <div className="d-inline add-dataset-title mb-2">{modalHeader}</div>
            </div>
            <div className="col-auto pad-l-0">
              <div className="card choosefile-card">
                <div className="col-12">
                  <div className="d-flex flex-column justify-content-space-evenly">
                    {/* <div className="d-flex flex-row"> */}
                    {mode === "update" && (
                      <div className="d-flex flex-row margin-bt">
                        <label style={{ fontWeight: "bold" }}> Name: </label>{" "}
                        <p className="username" style={{ marginLeft: "52px" }}>{currentUser?.username}</p>
                      </div>
                    )}
                    {mode === "add" && (
                      <div className="d-flex flex-row margin-bt">
                        <label style={{
                          fontWeight: "bold",
                          marginTop: "7px"
                        }}>Email: </label>
                        <input
                          type="email"
                          className="form-control shadow-none input-style-1"
                          value={currentUser?.email}
                          onChange={(e) =>
                            setCurrentUser((prevUser) => ({
                              ...prevUser,
                              email: e.target.value,
                            }))
                          }
                          autocomplete="off"
                        />
                      </div>
                    )}
                    {mode === "add" && (
                      <div className="d-flex flex-row margin-bt">
                        <label style={{
                          fontWeight: "bold",
                          marginTop: "7px"
                        }}>Name: </label>
                        <input
                          type="text"
                          className="form-control shadow-none input-style-2"
                          value={currentUser?.username}
                          onChange={(e) =>
                            setCurrentUser((prevUser) => ({
                              ...prevUser,
                              username: e.target.value,
                            }))
                          }
                          autocomplete="off"
                        />
                      </div>)}

                    {(mode === "update" || mode === "add") && (
                      <div className="d-flex flex-row margin-bt">
                        <label style={{
                          fontWeight: "bold",
                          marginTop: "7px"
                        }}>Password: </label>
                        <input
                          type={showPassword ? "text" : "password"} // Update the `type` attribute

                          className="form-control shadow-none input-style-6"
                          value={currentUser?.password}
                          onChange={(e) =>
                            setCurrentUser((prevUser) => ({
                              ...prevUser,
                              password: e.target.value,
                            }))
                          }
                          autoComplete="new-password" // Use this attribute
                          name={`password-${Math.random()}`} // Unique name

                        />
                        <button
                          type="button"
                          className="btn btn-link position-absolute"
                          onClick={() => setShowPassword((prev) => !prev)} // Add this to toggle the `showPassword` state







                          style={{
                            right: "87px",
                            fontSize: "16px",
                          }}
                        >
                          <i className={`fa ${showPassword ? "fa-eye-slash" : "fa-eye"}`} style={{ color: "black" }}></i>
                        </button>

                      </div>

                    )}

                    {/* </div> */}
                    <div className="d-flex flex-row margin-bt">
                      <label style={{
                        fontWeight: "bold",
                        marginTop: "7px"
                      }}>Role: </label>
                      <select
                        className="form-control shadow-none input-style-3"
                        name="role"
                        value={currentUser.role}
                        onChange={setUserRole}
                      >
                        <option disabled value="">
                          Select an option
                        </option>
                        {roleTypes.map((ele) => (
                          <option key={ele.name} value={ele.name}>
                            {ele.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="d-flex flex-row justify-content-space-evenly margin-bt">
                    <div style={{
                      marginLeft: "97px",
                      marginBottom: " 10px"
                    }}>
                      <label style={{ fontWeight: "bold" }}>
                        <input
                          type="radio"
                          value="assign"
                          checked={creditAction === "assign"}
                          onChange={changeCreditAction}
                        />
                        <span style={{ marginLeft: "10px" }}>Assign</span>
                      </label>
                      <label style={{ marginLeft: "13px", fontWeight: "bold" }}>
                        <input
                          type="radio"
                          value="revoke"
                          checked={creditAction === "revoke"}
                          onChange={changeCreditAction}
                        />
                        <span style={{ marginLeft: "10px" }}>Revoke</span>
                      </label>
                    </div>
                    <br />

                  </div>
                  <div className="d-flex flex-row margin-bt">
                    <label style={{
                      fontWeight: "bold",
                      marginTop: "7px"
                    }}>Credits: </label>
                    <input
                      defaultValue={credits}
                      type="number"
                      name="credit_revoked"
                      className="form-control shadow-none input-style-4"
                      onChange={(e) => setCredits(Number(e.target.value))}
                    />
                  </div>
            {/* Categories Selection */}
            {console.log(allAciveCategories)}
       <div className="d-flex flex-row margin-bt">
        <label style={{ fontWeight: "bold", marginTop: "7px" }}>Categories:</label>
        <MultiSelect
          options={allCategories}
          value={allUserCategories}
          onChange={(selected) => setAllUserCategories(selected)}
          labelledBy="Select Category"
          className="input-style-5 custom-multi-select"
          hasSelectAll={true}
        />
      </div>


      {/* Database Selection */}
      <div className="d-flex flex-row margin-bt">
        <label style={{ fontWeight: "bold", marginTop: "7px", marginRight: "10px" }}>Database:</label>
        <MultiSelect
          options={alldatabase}
          value={database}
          onChange={(selected) => setDatabase(selected)}
          labelledBy="Select Database"
          className="input-style-5 custom-multi-select2"
          hasSelectAll={false}
          valueRenderer={(selected, _options) => {
            if (selected.length === 0) return "Select Database";
            if (selected.length <= 3) return selected.map(item => item.label).join(", ");
            return `${selected.length} selected`;
          }}
        />
      </div>                    
      {/* Tables Selection */}
      <div className="d-flex flex-row margin-bt">
        <label style={{ fontWeight: "bold", marginTop: "7px", marginRight: "36px" }}>Tables</label>
        <MultiSelect
          options={allTables}
          value={selectedTables}
          onChange={(selected) => setSelectedTables(selected)}
          labelledBy="Select Tables"
          className="input-style-5 custom-multi-select"
          hasSelectAll={false}
          valueRenderer={(selected, _options) => {
            if (selected.length === 0) return "Select Database";
            if (selected.length <= 3) return selected.map(item => item.label).join(", ");
            return `${selected.length} selected`;
          }}
        />
      </div>

                </div>
              </div>
              <div className="errorText">{error ? error : ""}</div>
              <Form>
                <div className="mt-2">
                  <div className="d-flex flex-row-reverse">
                    <Button
                      className="cancel-btn btn-sm"
                      variant="primary"
                      onClick={handleCancel}
                    >
                      {" "}
                      Cancel{" "}
                    </Button>
                    <Button
                      className="create-btn btn-sm"
                      variant="primary"
                      disabled={!enableUpdateUser}
                      onClick={handleSubmit}
                    >
                      {" "}
                      {submitButtonText}{" "}
                    </Button>
                  </div>
                </div>
              </Form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserForm;