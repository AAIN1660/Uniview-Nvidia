import React, { useState } from "react";
import "./CategoryModal.scss";
import Button from "react-bootstrap/Button";
import loginService from "../services/loginService";
import { useHistory } from 'react-router-dom';
function UserTimeout({handleChange}){

    const [sanityErrorMsg,]=useState("Your Session has expired due to inactivity")
    const history = useHistory();
    const handleroute=()=>{
    
        handleChange()
        loginService.logout()
        history.push("/login");
    }
    
    return(
        <>
      	<div>
			<div className="overlay">
				<div className="container h-100 d-flex justify-content-center align-items-center ">
                 
					<div className="p-2 bg-white rounded categoryModal p-20">
                    <div className="d-inline add-dataset-title  ">{"Session Timeout"}
							<i className="fa fa-times float-right" onClick={handleroute}></i>
						</div>

                        <div className="card mt-2 p-3">
									<p>{sanityErrorMsg}</p>
							<div className="row mt-2">
								<div className="col-12 text-center">
										<Button className="btn-sm btn-primary" onClick={handleroute}>Login</Button>
								</div>
							</div> 
						</div>
                        </div>
					</div> 
				</div>
			</div>
	
           
        </>
    )
}

export default UserTimeout;