import React, { useEffect } from "react";
import Container from "@material-ui/core/Container";
import Paper from "@material-ui/core/Paper";
import CircularProgress from "@material-ui/core/CircularProgress";
import { connect } from "react-redux";
import { fetchUserProfile } from "../actions/user";
import { makeStyles } from "@material-ui/core/styles";
import Typography from "@material-ui/core/Typography";
import Grid from "@material-ui/core/Grid";
import Button from "@material-ui/core/Button";
import Link from "@material-ui/core/Link"
const useStyles = makeStyles((theme) => {
  return {
    paper: {
      marginTop: theme.spacing(5),
      padding: theme.spacing(2),
    },
    username: {
      flexGrow: 1,
    },
  };
});

function UserProfile(props) {
  const { fetchUserProfile, user} = props;
  const {
    username,
    email,
    first_name,
    last_name,
    default_atty_organization,
    default_atty_name,
    default_atty_address_line_one,
    default_atty_address_line_two,
    default_atty_phone,
    default_bar_id,
    expungement_petition_template,
    sealing_petition_template,
  } = user;

  const profileLoading = !username;

  const classes = useStyles();


  useEffect(() => {
    fetchUserProfile();
  }, []);
  return (
    <Container>
      <Paper className={classes.paper}>
        {profileLoading ? (
          <CircularProgress />
        ) : (
          <Grid container spacing={3}>
            <Grid container direction="row" item xs={12}>
              <Grid item className={classes.username}>
                <Typography variant="h3">{username}</Typography>
              </Grid>
              <Grid item>
                <Button href="profile/edit">Edit</Button>
              </Grid>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">{email}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">{`${first_name} ${last_name}`}</Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="h5">Default Attorney information</Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="body2">
                The attorney details here will populate by default in petitions you generate.
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">
                Organization: {default_atty_organization}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">
                {default_atty_address_line_one}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">
                {default_atty_address_line_two}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">{default_atty_name}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">{default_atty_phone}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body1">{default_bar_id}</Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="h5">Petition Template</Typography>
            </Grid>
            <Grid item xs={6}>
            {expungement_petition_template ? 
              <Link href={`api/record/templates/expungement/${expungement_petition_template}/`}>Expungement Petition Template</Link>
            : <Typography variant="body1">No Expungment Template Set</Typography>
            }
              </Grid>
            <Grid item xs={6}>
              {
                sealing_petition_template ? 
                <Link href={`api/record/templates/sealing/${sealing_petition_template}/`}>Sealing Petition Template</Link>
                : <Typography variant="body1">No Sealing Template Set</Typography>
              }
            </Grid>


          </Grid>
        )}
      </Paper>
    </Container>
  );
}

function mapStateToProps(state) {
  return {
    user: state.user,
  };
}

function mapDispatchToProps(dispatch) {
  return {
    fetchUserProfile: () => {
      dispatch(fetchUserProfile());
    },
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(UserProfile);
