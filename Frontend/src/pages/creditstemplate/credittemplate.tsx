import React, { useEffect, useState } from "react";
import { useTable, usePagination, useSortBy } from "react-table";
import { trackPromise } from "react-promise-tracker";
import { MultiSelect } from "react-multi-select-component";
import Card from "react-bootstrap/Card";
import moment from "moment";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import usercreditsService from "../../api/creditmanagementService";
import useCredit from "../../api/userCredit";
import "./credittemplate.scss";

const Creditstemplate: React.FC<{}> = () => {
  const [creditHistoryList, setCreditHistoryList] = useState([]);
  const [creditType, setCreditType] = useState("All");
  const { creditBalance } = useCredit();
  const pageSize = 10;
  const email = localStorage.getItem("email");
  const role = localStorage.getItem("role");
  console.log(role);

  const loggedInUser = localStorage.getItem("name");
  const [originalCreditHistoryList, setOriginalCreditHistoryList] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState(originalCreditHistoryList);
  const [fromDate, setFromDate] = useState(moment().startOf("month").format("DD-MM-YYYY"));
  const [toDate, setToDate] = useState(moment().format("DD-MM-YYYY"));
  const [usernames, setUsernames] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState([{ label: loggedInUser, value: loggedInUser }]
  );
  const [loaderMessage, setLoaderMessage] = useState("Fetching transactions...");
  const [loading, setLoading] = useState(true);
  const [userOptions, setUserOptions] = useState([]);
  const [userOptionsLoading, setUserOptionsLoading] = useState(true);

  useEffect(() => {
    transactionDetails(email);
  }, [email]);


  /*api call to fetch usersdetails for dropdown */
  useEffect(() => {
    const fetchUsers = () => {
      if (email !== "") {
        trackPromise(
          usercreditsService
            .fetchUsers()
            .then((response) => {
              const usersArray = response.data.users;

              console.log('====================================');
              console.log(usersArray);
              console.log('====================================');

              if (Array.isArray(usersArray)) {
                // Filter users based on role
                const filteredUsers = usersArray.filter((user) => {
                  if (role === "Admin") {
                    return user.role !== "superAdmin"; // Exclude superAdmin for Admins
                  }
                  return true; // superAdmin sees all users
                });

                const userNamesFromApi = filteredUsers.map((user) => user.username);
                const userOptions = userNamesFromApi.map((username) => ({ label: username, value: username }));

                setUserOptions(userOptions);
                setUsernames(userNamesFromApi);
                setUserOptionsLoading(false);
                setUsers(filteredUsers); // Set the filtered users
              } else {
                console.error("Invalid API response format. 'users' property is missing or not an array.");
              }
            })
            .catch((err) => {
              alert(err.response?.data?.error || "Error fetching users");
            })
        );
      }
    };

    fetchUsers();
  }, [email, role]); // Add role as a dependency


  const transactionDetails = (email) => {
    setLoading(true);
    trackPromise(
      usercreditsService
        .usertransctiondetails(email)
        .then((response) => {
          setOriginalCreditHistoryList(response.data.transactions);
          filterData(fromDate, toDate);
          setLoading(false);
        })
        .catch((err) => {
          setLoading(false);
          console.error("API Error:", err);
          alert(err.response.data.error);
        })
    );
  };

  const filterData = (fromDate, toDate) => {
    const filteredResult = originalCreditHistoryList.filter((item) => {
      const transactionDate = moment(item.Date, "YYYY-MM-DD HH:mm:ss").format("DD-MM-YYYY");
      const isDateInRange =
        moment(transactionDate, "DD-MM-YYYY") >= moment(fromDate, "DD-MM-YYYY") &&
        moment(transactionDate, "DD-MM-YYYY") <= moment(toDate, "DD-MM-YYYY");

      const isCreditTypeMatch =
        creditType === "All" ||
        (creditType === "creditassigned" && item["Credit Assigned"] > 0) ||
        (creditType === "creditused" && item["Credit Used"] > 0);

      // Exclude rows where critical fields are missing
      const hasRequiredData = item["Reference Id"] && item.Date && item["Transaction Type"];

      return isDateInRange && isCreditTypeMatch && hasRequiredData;
    });

    setFilteredTransactions(filteredResult);
  };


  useEffect(() => {
    filterData(fromDate, toDate);
  }, [creditType, originalCreditHistoryList]);

  const columns = React.useMemo(
    () => [
      { Header: "Reference Id", accessor: "Reference Id" },
      { Header: "Date", accessor: "Date" },
      { Header: "Transaction Type", accessor: "Transaction Type" },
      { Header: "Credit Used", accessor: "Credit Used" },
      { Header: "Credit Assigned", accessor: "Credit Assigned" },
      { Header: "Balance", accessor: "Balance" },
    ],
    []
  );

  const data = React.useMemo(() => filteredTransactions, [filteredTransactions]);

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    prepareRow,
    page,
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
    state: { pageIndex },
  } = useTable(
    {
      columns,
      data,
      initialState: { pageIndex: 0, pageSize },
    },
    useSortBy,
    usePagination
  );

  const handleFromDateChange = (e) => {
    const formattedFromDate = moment(e.target.value).format('DD-MM-YYYY');
    setFromDate(formattedFromDate);
    filterData(formattedFromDate, toDate);
  };

  const handleToDateChange = (e) => {
    const formattedToDate = moment(e.target.value).format('DD-MM-YYYY');
    setToDate(formattedToDate);
    filterData(fromDate, formattedToDate);
  };

  /*based on the dropdown selection fetching user tranctionhistroy*/
  const handleUserDropdownChange = (selectedUsername) => {
    const selectedUser = users.find((user) => user.username === selectedUsername?.value);
    const userEmail = selectedUser.email;
    if (userEmail) {
      transactionDetails(userEmail)
      setSelectedUser([selectedUsername]);
    }
  };

  return (
    <div className="creditTemplate">
      <div className="container-fluid">
        <div className="row mt-3 transaction-history-header categoryheader">
          <div className="col-4">
            <div className="left-header">
              <div
                className={
                  role === "Admin" || role === "superAdmin"
                    ? "text-creditHistory-admin"
                    : "text-creditHistory-general"
                }
              >
                Credit History
              </div>

              {role !== "General" && (
              //   <MultiSelect
              //   options={userOptions.map((option) => ({
              //     ...option,
              //     label: (
              //       <span title={option.label} style={{ display: "inline-block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              //         {option.label}
              //       </span>
              //     ),
              //   }))}
              //   value={selectedUser}
              //   onChange={(val) => handleUserDropdownChange(val[val.length - 1])}
              //   labelledBy="Select"
              //   hasSelectAll={false}
              //   selectionLimit={1}
              //   isLoading={userOptionsLoading}
              //   disabled={userOptionsLoading}
              // />

              <MultiSelect
                 options={userOptions}
                 value={selectedUser}
                 onChange={(val) => {
                   handleUserDropdownChange(val[val.length - 1]);
                 }}
                 labelledBy="Select"
                 hasSelectAll={false}
                 selectionLimit={1}
                 isLoading={userOptionsLoading}
                 disabled={userOptionsLoading}
                 className="custom-multi-select"
               />

              
              
              )}
            </div>
          </div>
          <div className="col-8">
            <div className="right-header">
              <div style={{ display: "flex", justifyContent: "space-around", alignItems: "center" }}>
                <span className="paddedspan">
                  <label className="radio-btnname">
                    <input
                      type="radio"
                      className="mx-1 Radio-Input"
                      name="creditType"
                      value="All"
                      onChange={() => setCreditType("All")}
                      checked={creditType === "All"}
                    />
                    All
                  </label>
                </span>
                <span className="paddedspan">
                  <label className="radio-btnname">
                    <input
                      type="radio"
                      className="mx-1  Radio-Input"
                      name="creditType"
                      value="creditassigned"
                      onChange={() => setCreditType("creditassigned")}
                      checked={creditType === "creditassigned"}
                    />
                    Credit Assigned
                  </label>
                </span>
                <span className="paddedspan">
                  <label className="radio-btnname">
                    <input
                      type="radio"
                      className="mx-1 Radio-Input"
                      name="creditType"
                      value="creditused"
                      onChange={() => setCreditType("creditused")}
                      checked={creditType === "creditused"}
                    />
                    Credit Used
                  </label>
                </span>
                <div className="" style={{ display: 'flex', width: "250px", alignItems: "center", marginLeft: "10px" }}>
                  <label className="label" >From Date :</label>
                  <input
                    type="date"
                    style={{ marginLeft: "5px", width: "150px" }}
                    className="form-control"
                    title="From Date"
                    value={moment(fromDate, 'DD-MM-YYYY').format('YYYY-MM-DD')}
                    max={moment(toDate, 'DD-MM-YYYY').format('YYYY-MM-DD')}
                    onChange={handleFromDateChange}
                  ></input>
                </div>
                <div className="" style={{ display: 'flex', width: "250px", alignItems: "center", marginLeft: "10px" }}>
                  <label className="label">End Date :</label>
                  <input
                    type="date"
                    style={{ marginRight: "11px", width: "150px" }}
                    className="form-control"
                    title="To Date"
                    value={moment(toDate, 'DD-MM-YYYY').format('YYYY-MM-DD')}
                    min={moment(fromDate, 'DD-MM-YYYY').format('YYYY-MM-DD')}
                    max={moment().format('YYYY-MM-DD')}
                    onChange={handleToDateChange}
                  ></input>
                </div>
              </div>
            </div>
          </div>

          {/* Filters and Radio Buttons */}

        </div>

        <div className="row">
          <div className="col">
            <div style={{ padding: "20px" }}>
              <table {...getTableProps()} className="table">
                <thead>
                  {headerGroups.map((headerGroup) => (
                    <tr {...headerGroup.getHeaderGroupProps()}>
                      {headerGroup.headers.map((column) => (
                        <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                          {column.render("Header")}
                          <span>
                            {column.isSorted ? (column.isSortedDesc ? " 🔽" : " 🔼") : ""}
                          </span>
                        </th>
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
    pageOptions.map((_, index) => {
      const startRange = Math.max(pageIndex - 2, 0);
      const endRange = Math.min(pageIndex + 2, pageOptions.length - 1);

      // Display logic for the range
      if (index === 0 || index === pageOptions.length - 1 || (index >= startRange && index <= endRange)) {
        return (
          <button
            key={index}
            onClick={() => gotoPage(index)}
            className={`btn ${pageIndex === index ? "active" : ""}`}
            type="button"
          >
            {index + 1}
          </button>
        );
      } else if (index === startRange - 1 || index === endRange + 1) {
        // Add ellipsis for skipped sections
        return (
          <span key={index} className="btn ellipsis">
            ...
          </span>
        );
      }
      return null;
    })}

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
      {loading && <LoadingOverlay message={loaderMessage} />}
    </div>
  );
};

export default Creditstemplate;
