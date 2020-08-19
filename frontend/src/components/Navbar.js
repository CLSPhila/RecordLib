import React from "react";
import { connect } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import AppBar from "@material-ui/core/AppBar";
import Typography from "@material-ui/core/Typography";
import Button from "@material-ui/core/Button";
import IconButton from "@material-ui/core/IconButton";
import Toolbar from "@material-ui/core/Toolbar";
import MenuIcon from "@material-ui/icons/Menu";
import { Link as RouterLink } from "react-router-dom";
import Link from "@material-ui/core/Link";
import Menu from "@material-ui/core/Menu";
import MenuItem from "@material-ui/core/MenuItem";
import { logout } from "frontend/src/api";

// The use of React.forwardRef will no longer be required for react-router-dom v6.
// See https://github.com/ReactTraining/react-router/issues/6056
const LinkToAbout = React.forwardRef((props, ref) => (
  <RouterLink innerRef={ref} {...props} />
));

const LinkToHome = React.forwardRef((props, ref) => (
  <RouterLink innerRef={ref} to="/" {...props} />
));

const useStyles = makeStyles((theme) => ({
  root: {
    flexGrow: 1,
  },
  menuButton: {
    marginRight: theme.spacing(2),
  },
  title: {
    flexGrow: 1,
    color: "#dee2e6",
  },
  buttonText: {
    color: "#dee2e6",
  },
  secondMenu: {
    backgroundColor: "#dee2e6",
  },
}));

const Navbar = (props) => {
  const { username } = props;
  const userMenuLabel =
    !username || username !== "" ? username : "Anonymous User";
  const classes = useStyles();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const localLogout = () => {
    setAnchorEl(null);
    logout();
  };

  return (
    <div className={classes.root}>
      <AppBar position="static">
        <Toolbar>
          <IconButton
            edge="start"
            className={classes.menuButton}
            color="inherit"
            aria-label="menu"
          >
            <MenuIcon />
          </IconButton>
          <Link className={classes.title} component={LinkToHome} to="/">
            <Typography variant="h6" className={classes.title}>
              Clean Slate Buddy
            </Typography>
          </Link>
          <Button
            aria-controls="simple-menu"
            color="inherit"
            aria-haspopup="true"
            onClick={handleClick}
          >
            {userMenuLabel}
          </Button>
          <Menu
            id="user-menu"
            anchorEl={anchorEl}
            keepMounted
            open={Boolean(anchorEl)}
            onClose={handleClose}
            anchorOrigin={{
              vertical: "bottom",
              horizontal: "left",
            }}
            getContentAnchorEl={null}
          >
            <MenuItem
              onClick={handleClose}
              component={RouterLink}
              to="/profile"
            >
              My Profile
            </MenuItem>
            <MenuItem onClick={localLogout}>Logout</MenuItem>
          </Menu>
          <Button
            color="primary"
            className={classes.buttonText}
            component={LinkToAbout}
            to="/about"
          >
            About
          </Button>
        </Toolbar>
      </AppBar>

      <AppBar position="static" color="inherit">
        <Toolbar>
          <Button
            color="primary"
            className={classes.buttonText}
            component={RouterLink}
            to="/applicant"
          >
            <Typography color="textSecondary"> Applicant </Typography>
          </Button>

          <Button
            color="primary"
            className={classes.buttonText}
            component={RouterLink}
            to="/attorney"
          >
            <Typography color="textSecondary"> Attorney </Typography>
          </Button>

          <Button
            color="primary"
            className={classes.buttonText}
            component={RouterLink}
            to="/sourcerecords"
          >
            <Typography color="textSecondary"> Sources (Dockets) </Typography>
          </Button>
          <Button
            color="primary"
            className={classes.buttonText}
            component={RouterLink}
            to="/criminalrecord"
          >
            <Typography color="textSecondary"> Cases </Typography>
          </Button>
          <Button
            color="primary"
            className={classes.buttonText}
            component={RouterLink}
            to="/analysis"
          >
            <Typography color="textSecondary"> Analysis </Typography>
          </Button>
          <Button
            color="primary"
            className={classes.buttonText}
            component={RouterLink}
            to="/petitions"
          >
            <Typography color="textSecondary"> Petitions </Typography>
          </Button>
        </Toolbar>
      </AppBar>
    </div>
  );
};

const mapStateToProps = (state) => {
  return {
    username: state.user.username,
  };
};

const NavbarConnected = connect(mapStateToProps)(Navbar);

export default NavbarConnected;
