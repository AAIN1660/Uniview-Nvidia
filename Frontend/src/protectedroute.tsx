import React from 'react'
import { useNavigate,Navigate } from 'react-router-dom';

const ProtectedRoute: React.FC<{
  redirectTo: string;
  children: React.ReactNode;
}> = ({ redirectTo, children }) => {
    const accessToken = localStorage.getItem("accessToken"); 
    return !! accessToken ? <>{children}</> : <Navigate to={redirectTo} />;
};


export default ProtectedRoute