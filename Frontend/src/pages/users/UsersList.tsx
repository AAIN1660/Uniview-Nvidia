import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

import UserForm from "../../modals/UserForm";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import { User } from "../../types";

import "./UsersList.scss";

import { trackPromise } from "react-promise-tracker";
import usercreditsService from "../../api/creditmanagementService";
import categoryService from "../../api/categoryService";
import Button from "react-bootstrap/Button";

import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  flexRender,
  ColumnDef,
} from "@tanstack/react-table";

type UsersListProps = {
  setIsAdmin?: React.Dispatch<React.SetStateAction<boolean>>;
  signOutClickHandler?: () => void;
  tabId?: string;
};

const UsersList: React.FC<UsersListProps> = ({ setIsAdmin, signOutClickHandler, tabId }) => {
  const [isAdminNew, setIsAdminNew] = useState(
    localStorage.getItem("role") === "Admin"
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [categoryLoading, setCategoryLoading] = useState<boolean>(true);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [updateUserObj, setUpdateUserObj] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [creditPoolBalance, setCreditPoolBalance] = useState<number>(0);
  const [useCreditPool, setUseCreditPool] = useState<boolean>(false);
  const [loaderMessage, setLoaderMessage] = useState("Fetching Users...");
  const [categoryLoaderMessage, setcategoryLoaderMessage] = useState(
    "Fetching Users..."
  );
  const [allCategories, setAllCategories] = useState([]);
  const userEmail = localStorage.getItem("email");
  const [modalMode, setModalMode] = useState<"add" | "update">("add");
  const [isEditing, setIsEditing] = useState(false);
  const [categoriesres, setCategoriesres] = useState([]);

  const navigate = useNavigate();
  console.log("inside usersList: ")

  // ADDITION: Search State
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);

  const columns: ColumnDef<User>[] = [
    { accessorKey: "username", header: "User Name" },
    { accessorKey: "email", header: "Email" },
    { accessorKey: "role", header: "Role" },
    { accessorKey: "file_uploaded", header: "File Upload" },
    { accessorKey: "query_count", header: "Query Count" },
    { accessorKey: "credit_assigned", header: "Credit Assigned" },
    { accessorKey: "credit_used", header: "Credits Used" },
    { accessorKey: "credit_revoked", header: "Credits Revoked" },
    { accessorKey: "balance", header: "Balance" },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) =>
        row.original.status === 1 ? (
          <span className="badge active-status">Active</span>
        ) : (
          <span className="badge bg-danger">Inactive</span>
        ),
    },
    {
      accessorKey: "action",
      header: "Action",
      cell: ({ row }) => (
        <>
          <i
            className="fa fa-pencil"
            style={{ color: "#222", marginRight: "10px" }}
            title="Edit User"
            onClick={() => updateUser(row.original)}
          ></i>

          {console.log(row)}

          {row.original.status === 1 ? (
            <i
              className="fa fa-solid fa-toggle-on text-success"
              style={{ color: "#222" }}
              title="Deactivate User"
              onClick={() =>
                changeUserStatus({ status: 0, email: row.original.email })
              }
            ></i>
          ) : (
            <i
              className="fa fa-solid fa-toggle-off text-danger"
              style={{ color: "#222" }}
              title="Activate User"
              onClick={() =>
                changeUserStatus({ status: 1, email: row.original.email })
              }
            ></i>
          )}
        </>
      ),
    },
  ];

  const changeUserStatus = ({ status, email }) => {
    const confirmMessage =
      status === 1
        ? "Are you sure you want to activate this user?"
        : "Are you sure you want to deactivate this user?";
    const confirmDelete = window.confirm(confirmMessage);

    if (confirmDelete) {
      setLoading(true);
      trackPromise(
        usercreditsService
          .updateuserstatus({ status, email })
          .then(() => {
            fetchUsers();
            if (email === userEmail) {
              signOutClickHandler?.();
            }
          })
          .catch(() => setLoading(false))
      );
    }
  };

  const fetchUsers = () => {
    setLoading(true);
    console.log("line 127")
    trackPromise(
      usercreditsService
        .fetchUsers()
        .then((response) => {
          console.log("line 132")
          const { config, users } = response.data;
          users?.forEach((user) => {
            if (user.email === userEmail && user.role !== "Admin" && user.role !== "superAdmin") {
              console.log("line 136")
              setIsAdmin?.(false);
              navigate("/layout/chat");
            }
          });

          // setUsers(users);
          // setFilteredUsers(users); // ADDITION: Initialize filtered users

          let newUsers = []
          console.log("Users: ", users)
          console.log("isAdmin: ", isAdminNew)

          if (isAdminNew) {
            newUsers = users.filter((user) => user.role !== "superAdmin")
            console.log("newUsers1: ", newUsers)
            setUsers(newUsers);
            setFilteredUsers(newUsers);
          }
          else {
            setFilteredUsers(users);
            setUsers(users);
          }
          console.log("newUsers: ", newUsers)
          // setUsers(newUsers)
          setCreditPoolBalance(config.credit_pool_balance);
          setUseCreditPool(config.use_credit_pool);
          setLoading(false);
        })
        .catch(() => setLoading(false))
    );
  };

  let categoryListLoaded = false;
  const getCategoryList = () => {
    if (categoryListLoaded) return; // Prevent multiple calls
    categoryListLoaded = true;
    console.log('====================================');
    console.log("1");
    console.log('====================================');
    setCategoryLoading(true);
    trackPromise(
      categoryService
        .getCategory({ type: "active" })
        .then((res) => {
          const activeCategories = res?.data?.CategoryList.filter(
            (category) => category.status === 1
          );
          const comboboxOptions = activeCategories.map((category) => ({
            value: category.id,
            label: category.category_name,
          }));
          setCategoriesres(activeCategories)
          setAllCategories(comboboxOptions);
          setLoading(false)
          setCategoryLoading(false);
        })
        .catch(() => setCategoryLoading(false))
    );
  };

  // ADDITION: Handle Search Input
  const handleSearch = (e) => {
    if (isEditing) return; 
    const query = e.target.value.toLowerCase();
    setSearchQuery(query);
    const filtered = users.filter(
      (user) =>
        user.username.toLowerCase().includes(query) ||
        user.email.toLowerCase().includes(query) ||
        user.role.toLowerCase().includes(query)
    );
    setFilteredUsers(filtered);
  };

  useEffect(() => {
    fetchUsers();

    getCategoryList();
  }, [tabId === "users"]);

  // useEffect(() => {
  //   getCategoryList();

  // }, [tabId === "users"])

  const closeModal = () => {
    setShowModal(false);
    setUpdateUserObj(null);
  };

  const updateUser = (userObj: User) => {
    setIsEditing(true);  
    setModalMode("update");
    setUpdateUserObj(userObj);
    setShowModal(true);
    setIsEditing(false);  
  };

  const addUser = () => {
    setSearchQuery("")
    setLoading(true)
    getCategoryList();

    setUpdateUserObj(null);
    setModalMode("add");
    setShowModal(true);
  };

  const table = useReactTable({
    data: filteredUsers, // ADDITION: Use filtered users here
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  return (
    <div>
      <div className="row" style={{ width: '100%', marginTop: "-9px" }}>
        <div className="col-6">
          <div className="row">
            <div className="col-3" >
              <div className="text1 ms-4  ps-4 pt-2" style={{ marginTop: "9px" }} >Users</div>
            </div>
            <div className="col-9">
              <div className="serach-cls">
                <input
                  type="text"
                  placeholder="Search Users"
                  value={searchQuery}
                  onChange={handleSearch}
                  className="form-control"
                  style={{
                    width: "60%",
                    /* float: left; */
                    /* margin-right: 38px !important; */
                    paddingLeft: "0px",
                    marginLeft: "-54px",
                    marginTop: "7px",
                    textAlign: "center"

                  }}
                  autoComplete="off"
                />
              </div>
            </div>

          </div>

        </div>

        <div className="col-6">
          <div className="creditpool-div">

            <Button className="adddataset-btn" variant="primary" onClick={addUser}>
              <i className="fa-solid fa-plus me-2" />Add User
            </Button>
            {useCreditPool && (
              <div className="credit-pool-balance">
                Credit Pool Balance: {creditPoolBalance}
              </div>
            )}
            {/* ADDITION: Search Input */}

          </div>
        </div>
      </div>

      {loading && <LoadingOverlay message={loaderMessage} />}
      {categoryLoading && !loading && (
        <LoadingOverlay message={categoryLoaderMessage} />
      )}
      <div className="users-list" style={{ paddingTop: useCreditPool ? "20px" : "50px", width: '98%', marginLeft: '1%', marginRight: '1%' }}>
        <table className="table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pagination">
          {/* First Page Button */}
          <button
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            type="button"
            className="btn"
          >
            {"<<"}
          </button>

          {/* Previous Page Button */}
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            type="button"
            className="btn"
          >
            {"<"}
          </button>

          {/* Page Numbers */}
          {Array.from({ length: table.getPageCount() }, (_, index) => (
            <button
              key={index}
              onClick={() => table.setPageIndex(index)}
              className={`btn ${table.getState().pagination.pageIndex === index ? "active" : ""}`}
              type="button"
            >
              {index + 1}
            </button>
          ))}

          {/* Next Page Button */}
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            type="button"
            className="btn"
          >
            {">"}
          </button>

          {/* Last Page Button */}
          <button
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            type="button"
            className="btn"
          >
            {">>"}
          </button>
        </div>

      </div>
      {showModal && (
        <UserForm
          closeModal={closeModal}
          modalHeader={modalMode === "add" ? "Add User" : "Update User"}
          userObj={updateUserObj}
          fetchUsers={fetchUsers}
          useCreditPool={useCreditPool}
          creditPoolBalance={creditPoolBalance}
          setCreditPoolBalance={setCreditPoolBalance}
          allAciveCategories={allCategories}
          categoriesres={categoriesres}
          mode={modalMode}
        />
      )}
    </div>
  );
};

export default UsersList;
