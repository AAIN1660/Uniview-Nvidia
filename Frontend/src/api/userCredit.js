import { useContext } from 'react';
import CreditContext from './creditContext';

const useCredit = () => {
const { creditBalance, setCreditBalance } = useContext(CreditContext);

return { creditBalance, setCreditBalance };
};

export default useCredit;