import React, { useEffect, useState } from 'react';
import dbConnectionService from '../../api/dbConnectionService';
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import './ConnectionSettings.scss';


const ShowDatabase = ({ currentDBConnection, handleClose, currentDBConnectionName }) => {
  const [tableNames, setTableNames] = useState([]);
  const [tablesData, setTablesData] = useState([]);
  const [selectedTable, setSelectedTable] = useState({});
  const [isLoading, setIsLoading] = useState(true); // Add loading state
  const [index, setIndex] = useState(0);
  const [sampleData, setSampleData] = useState({});
  const [showSampleData, setShowSampleData] = useState(false);
  const [userSelectedTables, setuserSelectedTables] = useState([]);


  const email = localStorage.getItem("email");


  useEffect(() => {
    dbConnectionService
      .get_user_tables(email)
      .then((res) => {
        setuserSelectedTables(res.data.tables_list);
      })
      .catch(() => {
        alert("Error");
      });
      console.log('userSelectedTables', userSelectedTables)
      console.log('tableNames', tableNames)

    const transformedData = tableNames.filter(table => userSelectedTables.includes(table.table_name)).map((item) => ({
      id: item.id,
      db_connection_id: item.db_connection_id.toString(),
      table_name: item.table_name,
      table_desc: item.table_desc,
      columns: item.columns.map((column) => ({
        column_name: column.column_name, // using column_name or sample for column name
        column_desc: column.column_desc, // using column_desc or a default description
        column_id: column.column_id,
        column_type: column.column_type
      })),
    }));
    setTablesData(transformedData);
    if (tablesData.length > 0) {
      console.log("line 22 tablesData: ", tablesData)
      setSelectedTable(tablesData[0])
      console.log("line 24 selectedTable: ", selectedTable)
    }
  }, [tableNames]);

  console.log(tableNames)


  const getTableDetails = (id) => {
    setIsLoading(true); // Set loading to true when fetching starts
    dbConnectionService
      .getdatadictionary(id)
      .then((res) => {
        setTableNames(res.data.db_dictionary_data);
        setIsLoading(false); // Set loading to false when fetching ends
      })
      .catch(() => {
        alert("Error");
        setIsLoading(false); // Set loading to false even on error
      });
  };

  const getSampleData = () => {
    dbConnectionService
      .getSampleData(currentDBConnection)
      .then((res) => {
        setSampleData(res.data);
        setIsLoading(false); // Set loading to false when fetching ends
      })
      .catch((err) => {
        print(err)
        alert(err);
        setIsLoading(false); // Set loading to false even on error
      });
  }

  useEffect(() => {
    getTableDetails(currentDBConnection);
    getSampleData();
  }, [currentDBConnection]);
  if (isLoading) return <LoadingOverlay message="Loading..." />; // Show loader while loading

  // Handle input changes for table name, description, and column data
  const handleInputChange = (event, section, index, field) => {
    const { value } = event.target;
    console.log(value, section, index, field)
    console.log("selectedTable: ", selectedTable)
    if (section === 'table') {
      // Update table_name and table_description
      setSelectedTable(prevState => ({
        ...prevState,
        [field]: value
      }));
    } else if (section === 'columns') {
      // Update column_name and column_description for the selected column
      const updatedColumns = [...selectedTable.columns];
      updatedColumns[index][field] = value;
      setSelectedTable(prevState => ({
        ...prevState,
        columns: updatedColumns
      }));
    }
  };

  // Handle form submission (API call)
  const handleSubmit = (event) => {
    event.preventDefault();
    updateTableData(selectedTable); // Send updated data to API
    // alert('Data updated successfully!');
  };

  // Handle form submission (API call)
  const updateTableData = (selectedTable) => {
    dbConnectionService.updateDataDictionary(selectedTable)
      .then((response) => {
        alert(response.data.message);

        let newTablesData = tablesData.map((tableData) => {
          if (tableData.id === selectedTable.id) {
            return { ...selectedTable }; // Return a new object with the selectedTable's properties
          }

          return tableData; // Return the original tableData if no match
        });

        // Set the updated array to state
        setTablesData(newTablesData);

        // getAllDocuments();
        // setLoading(false);
      })
      .catch((err) => {
        // setLoading(false);
        alert(err);
      })
    // alert('Data updated successfully!');
  };


  // Inline CSS
  const styles = {
    container: {
      background: 'white',
      padding: '30px',
      borderRadius: '8px',
      boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
      width: '600px',
    },
    heading: {
      textAlign: 'center',
    },
    formGroup: {
      marginBottom: '15px',
    },
    label: {
      display: 'block',
      marginBottom: '5px',
    },
    input: {
      width: '100%',
      padding: '8px',
      margin: '5px 0',
      border: '1px solid #ccc',
      borderRadius: '4px',
    },
    button: {
      width: '25%',
      padding: '10px',
      backgroundColor: 'transparent',
      color: 'black',
      border: '1px solid #4CAF50',
      borderRadius: '4px',
      fontSize: '16px',
      cursor: 'pointer',
      marginTop: '10px',
    },
    buttonHover: {
      backgroundColor: '#45a049',
    },
    output: {
      marginTop: '20px',
      padding: '10px',
      backgroundColor: '#e7f4e7',
      borderRadius: '4px',
      border: '1px solid #4CAF50',
    },
    select: {
      width: '100%',
      padding: '8px',
      margin: '5px 0',
      border: '1px solid #ccc',
      borderRadius: '4px',
    },
    horizontalLayout: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    columnGroup: {
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '15px',
    },
    columnInput: {
      width: '48%',
      padding: '8px',
      margin: '5px 0',
      border: '1px solid #ccc',
      borderRadius: '4px',
    },
  };


  return (
    <div className='p-5'>

      <div className="" style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>{currentDBConnectionName}</h1>
        <i className="fa fa-times float-right" style={{ color: "#222", fontSize: "24px" }} onClick={handleClose}></i>
      </div>
      <div className='database-list mt-2'>
        <div className='tables-list' style={{ width: "481px", height: "300px", overflowY: "auto", overflowX: "hidden", border: "1px solid #ccc", padding: "10px" }}>
          {tablesData.length > 0 ? (
            tablesData.map((table, index) => (
              <p
                key={index}
                className={`${table.table_name === selectedTable.table_name ? 'selected-table-name' : 'table-name'}`}
                style={{
                  cursor: "pointer",
                  margin: "0.5rem 0",
                  padding: "0.5rem",
                  backgroundColor: table.table_name === selectedTable.table_name ? "#f0f0f0" : "transparent",
                  borderRadius: "4px",
                  color: "black",
                }}
                onClick={() => { setSelectedTable(table), setIndex(index) }}
              >
                {table.table_name}
              </p>
            ))
          ) : (
            <p style={{ color: "#888", textAlign: "center", margin: "1rem 0" }}>No tables available</p>
          )}
        </div>
        {/* <div style={{ width: "100%", height: "300px", overflowY: "auto", overflowX: "hidden", border: "1px solid #ccc", padding: "10px" }}>
                    {Object.keys(selectedTable).length > 0 ? (
                        <table className='mt-2' style={{ width: "100%", borderCollapse: "collapse", marginLeft: '0px !important' }}>
                            <thead>
                                <tr>
                                    <th style={{ borderBottom: "1px solid #ccc", padding: "8px" }}>Column Name</th>
                                    <th style={{ borderBottom: "1px solid #ccc", padding: "8px" }}>Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                {selectedTable.columns.map((column, index) => (
                                    <tr key={index}>
                                        <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>{column.name}</td>
                                        <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>{column.description}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <p style={{ color: "#888", textAlign: "center", margin: "1rem 0" }}>No table selected</p>
                    )}
                </div> */}
        <form onSubmit={handleSubmit} style={{ marginLeft: '30px' }}>
          {/* Table Name and Description */}


          <div style={{ display: 'flex', width: '800px', justifyContent: 'space-between', alignItems: "center" }}>
            <div style={styles.formGroup}>
              <label htmlFor="table_name" style={styles.label}>Table Name:</label>
              <input
                type="text"
                id="table_name"
                value={selectedTable.table_name}
                onChange={(e) => handleInputChange(e, 'table', null, 'table_name')}
                style={styles.input}
                readOnly
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="table_description" style={styles.label}>Table Description:</label>
              <input
                type="text"
                id="table_description"
                value={selectedTable.table_desc}
                onChange={(e) => handleInputChange(e, 'table', null, 'table_desc')}
                style={styles.input}
                readOnly
              />
            </div>
            <button className='view-sample-data' disabled={Object.keys(sampleData || {}).length < 1} onClick={(e) => {
              e.preventDefault();
              setShowSampleData(true)
            }
            }>View Sample Data</button>
          </div>

          {/* Sample Data */}

          {showSampleData && sampleData?.[selectedTable.table_name]?.length > 0 && <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <i className="fa fa-times float-right" style={{ color: "#222", fontSize: "15px" }} onClick={() => setShowSampleData(false)}></i>
            </div>
            <table className="min-w-full border-collapse border border-gray-300" style={{ marginLeft: 0, marginTop: "20px", width: 'auto' }}>
              <thead>
                <tr className="bg-gray-200">
                  {Object.keys(sampleData[selectedTable.table_name][0] || {})?.map(col => (
                    <th style={{ padding: "10px 10px" }}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sampleData[selectedTable.table_name]?.map(data => (
                  <tr>
                    {
                      Object.keys(sampleData[selectedTable.table_name][0] || {})?.map(col => (
                        <td style={{ padding: "5px 5px" }}>{data[col]}</td>
                      ))
                    }
                  </tr>
                ))}
              </tbody>
            </table>
          </div>}

          {/* Columns */}

          <h3>Columns</h3>
          {Object.keys(selectedTable).length > 0 && (selectedTable.columns.map((column, index) => (
            <div key={index} style={{ display: 'flex', width: '450px', justifyContent: 'space-between' }}>
              <div style={styles.formGroup}>
                <label htmlFor={`column_name_${index}`} style={styles.label}>Column Name:</label>
                <input
                  type="text"
                  id={`column_name_${index}`}
                  value={column.column_name}
                  onChange={(e) => handleInputChange(e, 'columns', index, 'column_name')}
                  style={styles.input}
                  readOnly
                />
              </div>

              <div className="form-group">
                <label htmlFor={`column_description_${index}`} style={styles.label}>Column Description:</label>
                <input
                  type="text"
                  id={`column_description_${index}`}
                  value={column.column_desc}
                  onChange={(e) => handleInputChange(e, 'columns', index, 'column_desc')}
                  style={styles.input}
                  readOnly
                />
              </div>
            </div>
          )))}

          <button type="submit" style={styles.button}>Submit</button>
        </form>
      </div>

    </div>
  )
}

export default ShowDatabase;