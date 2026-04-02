function generateAlphaNumericCode(length = 9) {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    const randomIndex = Math.floor(Math.random() * characters.length);
    result += characters[randomIndex];
  }
  return result;
}

const formatCurrentDate = () => {
  const date = new Date()
  const day = date.getDate().toString().padStart(2, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const year = date.getFullYear().toString();
  return `${month}/${day}/${year}`;
};

const statusLifeCycle = ["SR RAISE", "APPROVED", "SCHEDULED", "REVIEW & QUALITY CHECK", "COMPLETED", "DISPATCHED" ]

const stringToDate = (dateString) => {
  const [month, day, year] = dateString.split('/');
  if(!month || !day || !year) {
    return null;
  }
  return new Date(year, month - 1, day);
}

function isDate(value) {
  return value instanceof Date && !isNaN(value);
}

export {generateAlphaNumericCode, formatCurrentDate, statusLifeCycle, stringToDate, isDate}
