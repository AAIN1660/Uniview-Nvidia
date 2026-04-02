import React, { useState, useMemo, useEffect } from "react";
import { useTable, usePagination, useGlobalFilter } from "react-table";
import { Box, Button, Input, Stack, Text } from "@chakra-ui/react";
import dbConnectionService from "../../api/dbConnectionService";
import "./ConnectionSettings.scss";
import AddConnection from "./AddConnection";
import ShowDatabase from "./ShowDatabase";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";

const ConnectionSettings = ({ tabId }) => {
    const [openModal, setOpenModal] = useState(false);
    const [modalHeader, setModalHeader] = useState("Add Category");
    const [currentDBConnection, setCurrentDBConnection] = useState("");
    const [currentDBConnectionName, setCurrentDBConnectionName] = useState("");
    const [dbConnections, setDBConnections] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("")

    // Table data and columns
    const columns = useMemo(
        () => [
            { Header: "Database Name", accessor: "db_name" },
            { Header: "Host", accessor: "host" },
            { Header: "User", accessor: "username" },
        //     { Header: "Action", accessor: "action" ,
        //     Cell: ({ row }) => {         
        //         return (
        //         <div className="icon-container-table">
                    
        //             <i className="fa fa-refresh uploadiconcls" title="Refresh the Database" aria-hidden="true"
        //             onClick={() => refreshDatabase()}
        //             ></i>
                  
        //         </div>
        //         );
        //     },
        // }
        ],
        []
    );

    const data = useMemo(() => [
        {
            name: "COnnection Name",
            host: "abc",
            port: "abc",
            user: "abc",
            database: "abc",
        },
    ], []);

    const {
        getTableProps,
        getTableBodyProps,
        headerGroups,
        page,
        prepareRow,
        canPreviousPage,
        canNextPage,
        pageOptions,
        gotoPage,
        nextPage,
        previousPage,
        state: { pageIndex },
    } = useTable(
        {
            columns,
            data: dbConnections,
            initialState: { pageIndex: 0 },
        },
        useGlobalFilter,
        usePagination
    );

    // Handle opening the modal
    const handleOpen = () => setOpenModal(true);
    const handleClose = () => setOpenModal(false);

    const getDBConnections = () => {
        setMessage("Fetching Database Connection")
        setLoading(true)
        dbConnectionService.getDBConnections()

            .then((response) => {
                setDBConnections(response.data.db_conn_data);
                setLoading(false)
            })
            .catch((err) => {
                // setLoading(false);
                // alert(err.response.data.message);
            })
    }


    // const refreshDatabase = () => {
    //     console.log('refreshed')
        
    // };


    useEffect(() => {
        getDBConnections()
    }, [tabId === "database-connection"])

    // Validate form and create connection
    const handleCreateConnection = (formState) => {
        setMessage("Adding Database Connection")
        setLoading(true)
        const errors = {};
        Object.keys(formState).forEach((key) => {
            if (!formState[key].value) {
                errors[key] = `${formState[key].label} is required`;
            }
        });

        if (Object.keys(errors).length === 0) {
            const payload = {
                host: formState["host"].value,
                username: formState["username"].value,
                password: formState["password"].value,
                db_name: formState["db_name"].value,
            }
            dbConnectionService.createDBConnection(payload)
                .then((response) => {
                    alert(response.data.message);
                    // getAllDocuments();
                    setLoading(false);

                    handleClose()
                    getDBConnections()
                })
                .catch((err) => {
                    // setLoading(false);
                    alert(err.response.data.message);
                })
        }
    };


    function showDatabase(id, name) {
        setCurrentDBConnection(id)
        setCurrentDBConnectionName(name)

    }


    return (
        <>
            {loading && <LoadingOverlay message={message} />}
            <div className="connection-settings">
                {currentDBConnection ? (<ShowDatabase currentDBConnection={currentDBConnection} handleClose={() => setCurrentDBConnection("")} currentDBConnectionName={currentDBConnectionName} />) :
                    (
                        <div>
                            {
                                openModal &&
                                <AddConnection closeModal={handleClose} modalHeader={modalHeader} handleCreateConnection={handleCreateConnection} />
                            }
                            <div className="row mt-2">
                                <div className="add-connection" style={{ marginTop: "-15px" }}>
                                    <Button
                                        className="adddataset-btn me-5"
                                        variant="primary"
                                        onClick={() => {
                                            setModalHeader("Add New Connection");
                                            handleOpen();
                                        }}
                                    >
                                        <i className="fa-solid fa-plus me-2" /> Add Connection
                                    </Button>
                                </div>
                                <div className="col-12" style={{ marginTop: "27px" }}>
                                    <table className="table" {...getTableProps()} style={{
                                        width: "95%",
                                        left: "34px"
                                    }} >
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
                                                // console.log('row', row)
                                                prepareRow(row);
                                                return (
                                                    <tr {...row.getRowProps()}>
                                                        {row.cells.map((cell) => (
                                                            <td {...cell.getCellProps()} style={{ verticalAlign: "middle" }}>
                                                                {cell.column.Header === "Database Name" ? <Button className="connection-name-select" onClick={() => showDatabase(cell.row.original.id, cell.value)}
                                                                >{cell.value}</Button> : cell.render("Cell")}</td>
                                                        ))}
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>

                                    {/* Pagination Controls */}
                                    <div className="pagination me-4">
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
                        </div>)
                }


            </div >
        </>
    );
};

export default ConnectionSettings;
