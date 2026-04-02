import React, { useState, useEffect, Children } from "react";
import CreditContext from "./creditContext";
import axios from "axios";
import Layout from "../pages/layout/Layout";


const CreditProvider = ({
  children,
  setIsAdmin,
}) => {
  const [creditBalance, setCreditBalance] = useState(0);
  const email = localStorage.getItem("email");
  const api = axios.create({
    baseURL: import.meta.env.VITE_APP_API_URL,
    headers: { "Content-Type": "application/json" },
  });

  useEffect(() => {
    const fetchCreditBalance = async () => {
      api
        .get(`/userCreditService/get_user_balance?email=${email}`)
        .then((response) => {
          const { role, balance } = response.data;
          localStorage.setItem("role", role);
          setIsAdmin(role === "Admin");
          setCreditBalance(balance);
        })
        .catch((err) => {
          return;
        });
    };

    if (email !== null) {
      fetchCreditBalance();
    }
  }, [email]);

  return (
    <CreditContext.Provider value={{ creditBalance, setCreditBalance }}>
      {children}
    </CreditContext.Provider>
  );
};

export default CreditProvider;
