# Project Prompt Log

Purpose: reproducibility log of user prompts used in this project.

Note:
- I could not find prior-session prompt logs in this workspace.
- Logging starts from this entry onward.

## 2026-04-09

1. "Before entering the next steps suggested by you, there are two additional issues.

1. The core radius should be calculated evaluated in the direction of the track rather than the average forexample. So, if the Ribberink codebase does not have this directionality included, it should be added. Both average and directional radiuses should be reported.

2. Due to reproducability issues I need to report my prompts during the whole project. If the prompts of the previous sessions are not available (please check), we should start now. Make two additional project files where 1) the prompts and 2) prompts and your responses (just in case) are recorded. These files should be included in version control process and aknowledged appropriatelly in the README.md file."

2. "Please proceed to the next steps 1, 2 and 3."

3. "Please update the project_prompts_and_responses.md  project_prompts.md files regularily or every time there is a new prompt (prompt+response) so that the full sequence of our interaction is recorded. Include those files always in commits."

4. "Is it enough to save the preference in persistent memory or should it be stated in README.md file, which I would request to read in the beginning of a new session? I am a little doubtfull that the preference might be lost at some point if it is inly in your persistent memory. I did not know that you have that."

5. "About the .venv issue that we discussed earlier in this session: in /users/jfkarhu/Numlab/hurricane_kirk/requirements.txt it is said: \"# cfgrib, xarray, eccodes, pandas, numpy already in run_oifs .venv\". Based on this it seems possible to me that our earlier sessions were initiated or directed to /users/jfkarhu/Numlab/run_oifs instead of /users/jfkarhu/Numlab/hurricane_kirk even though all the project material is in /users/jfkarhu/Numlab/hurricane_kirk. Would it make sense to kill/delete the venv in /users/jfkarhu/Numlab/run_oifs and migrate permanently and explicitly to /users/jfkarhu/Numlab/hurricane_kirk? If so, please, suggest/make necessary changes both in venvs and requirements.txt (is this relevant to mention in README.md?)."

6. "Please, commit and push these four updates now."

7. "Sorry, your request failed. Please try again.

Copilot Request id: f73fdbf2-0860-4ae4-8d1a-611516e77494

GH Request Id: AEAE:17DFA4:2C7B9A7:3117F3D:69D7A82D

Reason: token expired or invalid: 401

This possibly happened because the computing node session in Mahti was terminated due to time limit! What do you think, could it be?"

8. "I rceived this in Mahti:  Quota limit warning for /users/jfkarhu

	Using 9.76 GB of quota 10 GB. Consider deleting or archiving files to free up disk space. \""

9. "Run all four steps."

10. "Committ changes and push! lets wrap up for today."

## 2026-04-09 (new session)

11. "Check  /users/jfkarhu/Numlab/hurricane_kirk/README.md for the project status and let's continue from there!"

12. "Lets start taking the suggested steps in order!"

13. "Check 'hurricane_funcs.py' in Ribberink codebase for 'magnitude' function and other missing functions!"

14. "The process seems stalled."

15. "The CPS figure exists, but there are no graphs/lines/markers/dots ie. content in the plot, just two frames for lower and upper CPSs."

13. "Check \"hurricane_funcs.py\" in Ribberink codebase for \"magnitude\" function and other missing functions!"

## 2026-04-09 (continued session)

16. "Pursue option 2 now!"

17. "The output files for each runs: baserun: pwd"

18. "Are you sure the spectral file conversion was successful? You might want to check /users/jfkarhu/Numlab/run_oifs/post_process_oifs_python.bash for hints!"

## 2026-04-10

19. "I need to interrupt the process now for the day. Make necessary remarks on README.md so that you know where we stopped this time so that a smooth restart can happen tomorrow. Commit all changes and push!"

20. "Check /users/jfkarhu/Numlab/hurricane_kirk/README.md abd see where we stopped and please, continue the work from there!"

21. "It seems as if you are stuck. Please, investigate!"

22. "It seems you are stuck again!"

23. "There was connection problems, please try again!"

24. "There seems to be problems in continuing the project work. Try again, but, please, if you get stalled/stuck cancel the work yourself, if possible!"

25. "You have been loading something for quite a while and the process looks unresponsive again. Please investigate and retry!"

26. "First I have some questions about the ett_start_timing.png -plot. What are closed/full markers that appear once on the B-graphs and what do the vertical dashed lines that cross them signify?"

27. "Modify the colour coding of the runs to match that in track_comparison.png!"

28. "Regenarate ett_start_timing.png"

29. "Commit all changes and push!"

## 2026-04-13

30. "Firstly I have an issue about plotting:

1. The track_comparison.png -plot needs to be modified so that the polygon within which the initial SST were modified in -K, +K and +6K runs were modified will be displayed as well. The corner points of the polygon are:

1. 10 N, 30W
2. ⁠10 N, 45 W
3. ⁠20 N, 55W
4. ⁠30 N, 60 W
5. ⁠40 N, 55 W
6. ⁠50 N, 35 W
7. ⁠50 N, 15 W
8. ⁠35 N, 15 W
9. ⁠35 N, 35 W
10. ⁠30 N, 40 W
11. ⁠22.5 N, 35 W
12. ⁠17.5 N, 22.5W

Make the polygon visible in the plot by colouring the polygon are with c. 85 % transparent grey hue. Extend the plot area (lat/lon-wise) to include the polygon entirely to (to south until 5 N and to west until 65 W ). Keep the date annotation texts similarily relative to the original places as now)."

31. "Let's narrow and align the legend box more to right of the plot and allowing it to be higher: divide the "(big dots and crosses at 12UTC)" to two lines after "and". Make the font of that text 75 % smaller similarly to the "SST-perturbation polygon" explanatory text!"

32. "In /users/jfkarhu/Numlab/hurricane_kirk/notebooks/05_multi_run_comparison.ipynb there is cell "4. Cyclone Phase Phase Overlay". I do not find the output anywhere. Does it produce any?"

33. "Please elaborate the syntax of the path: plt.savefig('../plots/kirk_cps_overlay.png', dpi=150)!"

34. "Are the cells of this notebook independent from each other? Are they independent from the cells of the previous notebooks?"

35. "Please, run the notebooks!"

36. "Please, patch Cell 5 so IBTrACS loads robustly. Also include -3K run in all plots, including kirk_mslp_comparison.png!"

37. "Use the same colour coding of runs for all plots: fetc the coding from the plotting script for \"track_comparison.png\""

38. "Reverse the y-axis for kirk_mslp_comparison.png!"

39. "Out-reverse the y-axis for kirk_mslp_comparison.png!"

40. "For /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_cps.png apply the correct colour coding for the runs and add date and time annotation at 00UTC to the curves."

## 2026-04-14

41. "Can you confirm to me whether you are a GitHub Copilot CLI through my organization fmidev or an open, free version of Copilot?"

42. "When clicking a profile icon in VS Code UI (left down corner) it shows JuhaAKarhu (GitHub). JuhaAKarhu is my acount which has in principal access to GitHub Copilot CLI through my organization fmidev."

43. "Please, check those for me!"

44. "Let's leave the Copilot licence issue for now. Please read /users/jfkarhu/Numlab/hurricane_kirk/README.md and the log file /users/jfkarhu/Numlab/hurricane_kirk/COMPLETION_SUMMARY_2026-04-13.md in order to now what the project is about and where we left last time."

45. "I believe -3K did not appear due to this safe_name definition: \"safe_name = run_name.replace('+', 'p')\" which explicitly excluded minus mark and letter \"m\"!"

46. "Can't you do something like: safe_name = run_name.replace('+', 'p'; '-','m') or similar with correct syntax? Wouldn't that fix the problem?"

47. "Re-execute and re- validate wind-radius outputs from notebook 04."

48. "please, patch!"

41. "Let's wrap up for now! Please, update the log documents for smooth continuation of work next time, commit and push!"

40. "For /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_cps.png apply the correct colour coding for the runs and add date and time annotation at 00UTC to the curves."

---
## Session: April 14, 2026

49. "Read /users/jfkarhu/Numlab/hurricane_kirk/README.md to understand what the project is about and /users/jfkarhu/Numlab/hurricane_kirk/COMPLETION_SUMMARY_2026-04-13.md to understand where we left the last time of controlled end of session. Bear in mind that the last session was interrupted abruptly."

50. "Go on with the recommended next steps!"

51. "The plot /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_R17.png should be redrawn with max y-range 3000 km. the last timestep value of +3K run should be allowed to overshoot!"

52. "To plots /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_cps.png /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_mslp_comparison.png /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_R17.png add a bigger marker to denote the the ETT start time for each simulation. Use the same colorcoding just bigger mark for the start time. Get the ETT start times for each run from the ETT start time analysis."

53. "Check /users/jfkarhu/Numlab/hurricane_kirk/README.md, /users/jfkarhu/Numlab/hurricane_kirk/COMPLETION_SUMMARY_2026-04-14.md and /users/jfkarhu/Numlab/hurricane_kirk/project_prompts_and_responses.md to see where we left the last time session ended in controlled way or the last commit was made. Bear in mind though that some files may have been altered after the last commit as the last session was interrupted abruptly!"

54. "you should run .project_setup.sh to make git available, I believe!"

55. "Yes, please! [verify plots and re-run stale CPS plot]"

56. "commit!"

57. "Next, replot the /users/jfkarhu/Numlab/hurricane_kirk/plots/track_comparison.png with different name with the ETT start times displayed with big markers as in other comparison plots. For the best track, use the following timestep as the ETT start time: 6 Oct 1800 UTC. Add one more explanatory text to the legend box saying \"(biggest markers at ETT start time)\"."

58. "You should apply the ETT markers to the latest version of the plot where the polygon of the perturbed SSTs is displayed. Please, correct!"

59. "[Conversation handoff summary] The notebook 03 CPS output contains massive repeated warnings and recurring errors like 'Dataset object has no attribute lat'; is this output necessary for a final sealed/published repository, or can most/all of it be discarded?"

60. "Do the cleanup for notebook 3 and do similar tasks to notebooks 4 and 5, too, cause there seem to be similar warnings!"

61. "Let's clean the codebase further. The plots /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_cps_overlay.png /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_track_comparison.png /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_windradius_EW.png /users/jfkarhu/Numlab/hurricane_kirk/plots/kirk_windradius_NS.png /users/jfkarhu/Numlab/hurricane_kirk/plots/track_comparison_ett.png are not needed. Clean up the codebase from all notebook and script content that is related to plotting of those plots."

62. "Let's run the whole codebase in order to check, whether the needed plots are reproduced as earlier."

63. "According to the listing above, the timestamps show pre-cleanup times. Please verify again, that the cleaned up code actually produced these files! Otherwise try to produce them!"

64. "Please, do!"

65. "Are all those scripts still needed?"

66. "Do you actually mean to suggest moving the \"1. Keep\" scripts to scripts and remove/archive the \"2. Optional\" scripts?"

67. "Wouldn't it be cleaner to have all necessary scripts in scripts -directory (and perhaps the optional in dev_tools folder or optionally remove them totally)?!"

68. "Implement the full migration!"

69. "Please do and after that lets verify that the whole codebase is producing the expected results(plots!)"

70. "I think the COMPLETION summaries are not needed in the final version of the project? What do you think?"

71. "Move to docs/session_archive and commit!"

72. "Let's consider the README.md file. Do you think it is uptodate and reflect the current status of the project? Please check!"

73. "Patch the Readme file, but lets track the plots and include them to commit and final repo."
