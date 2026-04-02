import React, { useState } from 'react';
import { Box, Button, Input, Stack, Text } from "@chakra-ui/react";
import { trackPromise } from "react-promise-tracker";
import Alert from "react-bootstrap/Alert";
import Form from "react-bootstrap/Form";

const AddConnection = ({ closeModal, modalHeader, handleCreateConnection }) => {
    const [formState, setFormState] = useState({
        db_name: { label: "Database Name", "value": "" },
        host: { label: "Host", "value": "" },
        username: { label: "Username", "value": "" },
        password: { label: "Password", "value": "" }

    });
    // State for errors
    const [error, setError] = useState({});
    const [loading, setLoading] = useState(false);
        


    // Handle form input changes
    const handleInputChange = (e) => {
        const { name, value } = e.target;

        setFormState((prev) => ({
            ...prev,
            [name]: { label: prev[name].label, value: value },
        }));
    };

    return (
        <div className="addConnectionModal">
            <div className="container h-100">
                <div className="modal-header">
                    <h5>{modalHeader}</h5>
                    <i className="fa fa-times float-right" style={{ color: "#222", fontSize: "20px" }} onClick={closeModal}></i>
                </div>
                {Object.keys(formState).map((key) => (
                    <Box key={key} mb={4}>
                        <label>{formState[key].label.replace(/([A-Z])/g, " $1")}*</label>
                        <Input
                            name={key}
                            value={formState[key].value}
                            placeholder={`Enter ${formState[key].label}`}
                            onChange={handleInputChange}
                            isInvalid={!!error[key]}
                        />
                        {error[key] && <Text color="red.500">{error[key]}</Text>}
                    </Box>
                ))}
                <Form>
                    <div className="mt-4">
                        <div className="d-flex flex-row-reverse">
                            <Button
                                className="mt-2 cancel-btn btn-sm"
                                variant="primary"
                                onClick={closeModal}
                            >
                                {" "}
                                Cancel{" "}
                            </Button>
                            <Button
                                className="mt-2 create-btn btn-sm"
                                variant="primary"
                                onClick={() => handleCreateConnection(formState)}
                            >
                                {" "}
                                Submit{" "}
                            </Button>
                        </div>
                    </div>
                </Form>
            </div>
        </div>
    )
}

export default AddConnection;