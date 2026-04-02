import moment from "moment";

const DateTimeFormatter = (date) =>
moment(new Date(date)).format("MMM-DD-YYYY HH:mm");

const getSizeinKB = (bytes) => {
  return (bytes/1024).toFixed(2) + " Kb"
}

const YearFormat = () =>
moment(new Date()).format("YYYY");

export {
  DateTimeFormatter,
  getSizeinKB,
  YearFormat
};

