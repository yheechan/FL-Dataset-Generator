#include "../music_utility.h"
#include "smvb.h"

/* The domain for SMVB must be names of functions whose
   function calls will be mutated. */


// Global vector to store VarDecl nodes
std::vector<const ValueDecl*> VDs;
std::vector<const ValueDecl*> VD_refs;

bool SMVB::ValidateDomain(const std::set<std::string> &domain)
{
  return true;
}

bool SMVB::ValidateRange(const std::set<std::string> &range)
{
  // for (auto e: range)
 //    if (!IsValidVariableName(e))
 //      return false;

  return true;
}

void SMVB::setRange(std::set<std::string> &range) {}

// Return True if the mutant operator can mutate this expression
bool SMVB::IsMutationTarget(clang::Stmt *s, MusicContext *context)
{
  if (CompoundStmt *cs = dyn_cast<CompoundStmt>(s))
  {
    const Stmt* parent = GetParentOfStmt(s, context->comp_inst_);
    if (!parent)
      return false;

    if (isa<StmtExpr>(parent))
      return false;

    SourceManager &src_mgr = context->comp_inst_->getSourceManager();
    SourceLocation start_loc = cs->getLBracLoc();
    SourceLocation end_loc = cs->getRBracLoc().getLocWithOffset(1);

    // Do NOT apply SMVB to the then-body if there is an else-body
    if (isa<IfStmt>(parent))
    {
      auto if_stmt = cast<IfStmt>(parent);
      // cout << "if\n";
      // PrintLocation(src_mgr, if_stmt->getThen()->getBeginLoc());
      // PrintLocation(src_mgr, s->getBeginLoc());
      // cout << (!if_stmt->getElse()) << endl;

      if (if_stmt->getThen()->getBeginLoc() == s->getBeginLoc() &&
          if_stmt->getElse())
        return false;
    }

    // PrintLocation(src_mgr, start_loc);
    // PrintLocation(src_mgr, parent->getBeginLoc());
    // cout << parent->getStmtClassName() << endl;

    return context->IsRangeInMutationRange(SourceRange(start_loc, end_loc));
  }

  return false;
}

void SMVB::Mutate(clang::Stmt *s, MusicContext *context)
{
  CompoundStmt *cs;
  bool skip_up = false, skip_down = false;
  if (!(cs = dyn_cast<CompoundStmt>(s)))
    return;

  SourceManager &src_mgr = context->comp_inst_->getSourceManager();
  SourceLocation start_loc = cs->getLBracLoc();
  SourceLocation end_loc = cs->getRBracLoc().getLocWithOffset(1);
  string token{ConvertToString(s, context->comp_inst_->getLangOpts())};

  // CASE 1: MOVE BRACE UP 1 STMT = EXCLUDE LAST STATEMENT
  auto last_stmt = cs->body_begin();
  auto it = cs->body_begin();
  string mutated_token1{"{\n"};
  string check;
  const Stmt* parent = GetParentOfStmt(s, context->comp_inst_);
  if(isa<CXXTryStmt>(parent)){
    skip_up = true;
    skip_down = true;
  }
  // cout<<"####parent###"<<endl;
  // parent->dump();
  // cout<<"@@@@@@@@@@@@@@"<<endl;
  // cout<<hasDeclRef(parent)<<endl;
  // cout<<"@@@@@@@@@@@@@@"<<endl;
  // cout<<"####stmt###"<<endl;
  // s->dump();
  // cout<<"@@@@@@@@@@@@@@"<<endl;
  // cout<<hasDeclRef(s)<<endl;
  // cout<<"@@@@@@@@@@@@@@"<<endl;
  // cout<<"#######"<<endl;

  if(const ForStmt* fs = dyn_cast<ForStmt>(parent)){
    // cout<<"meimaobing"<<endl;
    const Stmt* init_for = fs->getInit();
    if(!init_for)
      goto null_init;
    // init_for->dump();
    if (DeclStmt const* declStmt = dyn_cast<DeclStmt>(init_for)) {
      // cout<<"meimaobingba"<<endl;
      // Collect the VarDecl nodes from the DeclStmt
      if (!VDs.empty()){
        VDs.clear();
      }
      for (DeclStmt::const_decl_iterator it = declStmt->decl_begin(); it != declStmt->decl_end(); ++it) {
        if (const ValueDecl* varDecl = dyn_cast<ValueDecl>(*it)) {
            VDs.push_back(varDecl);
            // cout<<"zheyemeimaobing"<<endl;
            // varDecl->dump();
        }
      }
    }
    if(hasDeclRef(s)){
      // cout<<"zhejiugengmeiwentile"<<endl;
      for (std::size_t i = 0; i < VDs.size(); ++i) {
        for (std::size_t j = 0; j < VD_refs.size(); ++j) {
        // VD->dump();
        // VDs[i]->dump();
          if(VD_refs[j] == VDs[i]){
            // cout<<"zuihouyiduosuo"<<endl;
            skip_up = true;
          }
        } 
      } 
    }
  }
  null_init:
  if (it == cs->body_end())
    goto case2;

  it++;

  for (; it != cs->body_end(); it++)
  {
    Stmt *temp = *last_stmt;
    mutated_token1 += ConvertToString(temp, context->comp_inst_->getLangOpts());

    if (!(isa<CompoundStmt>(temp) || isa<ForStmt>(temp) || isa<IfStmt>(temp) ||
          isa<NullStmt>(temp) || isa<SwitchCase>(temp) || 
          isa<SwitchStmt>(temp) || isa<WhileStmt>(temp) || isa<LabelStmt>(temp))) 
      mutated_token1 += ";";

    mutated_token1 += "\n";    
    last_stmt++;
  }

  if (isa<CaseStmt>(*last_stmt) || isa<SwitchCase>(*last_stmt) || 
      isa<LabelStmt>(*last_stmt))
    goto case2;

  // PrintLocation(src_mgr, start_loc);
  // PrintLocation(src_mgr, (*last_stmt)->getBeginLoc());
  // cout << (*last_stmt)->getStmtClassName() << endl;

  mutated_token1 += "}\n";

  //need to find way to solve
  //what is exprwithcleanup
  check = ConvertToString(*last_stmt, context->comp_inst_->getLangOpts());

  if(hasDeclRef(*last_stmt)){
    for(auto local_decl: (*(context->getSymbolTable()->getFuncLocalList()))[context->getFunctionId()]){
      string local_decl_name{local_decl->getNameAsString()};
      SourceLocation start_loc_decl = local_decl->getBeginLoc();
      for(std::size_t r = 0; r < VD_refs.size(); ++r){
        string ref_name{VD_refs[r]->getNameAsString()};
        // cout<<"local: "<<local_decl_name<<" ref: "<<ref_name<<" loc: "<<(end_loc < start_loc_decl)<<endl;
        // cout<<"###decl###"<<endl;
        // PrintLocation(src_mgr, start_loc_decl);
        // cout<<"###start###"<<endl;
        // PrintLocation(src_mgr, start_loc);
        // cout<<"#########"<<endl;
        if(local_decl_name == ref_name && start_loc < start_loc_decl){
          skip_up = true;
        }
      }
    }
  }


  if(check.find(".str()") != string::npos){
    skip_up = true;
  }
  //if the last stmt is a break statement
  if(isa<BreakStmt>(*last_stmt)){
    skip_up = true;
  }


  // (*last_stmt)->dump();
  mutated_token1 += ConvertToString(*last_stmt, 
                                    context->comp_inst_->getLangOpts());
  if (!(isa<CompoundStmt>(*last_stmt) || isa<ForStmt>(*last_stmt) || 
        isa<IfStmt>(*last_stmt) || isa<WhileStmt>(*last_stmt) ||
        isa<NullStmt>(*last_stmt) || isa<SwitchCase>(*last_stmt) || 
        isa<SwitchStmt>(*last_stmt) || isa<LabelStmt>(*last_stmt)))
    mutated_token1 += ";";
  
  mutated_token1 += "\n";
  if(!skip_up){
    context->mutant_database_.AddMutantEntry(context->getStmtContext(),
      name_, start_loc, end_loc, token, mutated_token1, 
      context->getStmtContext().getProteumStyleLineNum(), "UP");
    }

  // CASE 2: MOVE BRACE DOWN 1 STMT = INCLUDE LAST STATEMENT
  case2:
  const Stmt *second_level_parent = GetSecondLevelParent(s, context->comp_inst_);
  if (!second_level_parent)
    return;

  if (!isa<CompoundStmt>(second_level_parent))
    return;

  auto compound_grandparent = cast<CompoundStmt>(second_level_parent);
  
  // find the location of the parent
  auto it2 = compound_grandparent->body_begin();
  auto next_stmt = compound_grandparent->body_begin();
  next_stmt++;

  for (; it2 != compound_grandparent->body_end(); it2++)
  {
    if (!((*it2)->getBeginLoc() != parent->getBeginLoc() ||
          (*it2)->getEndLoc() != parent->getEndLoc()))
      break;

    next_stmt++;
  }

  if (next_stmt == compound_grandparent->body_end())
    return;

  end_loc = GetLocationAfterSemicolon(
      src_mgr, 
      TryGetEndLocAfterBracketOrSemicolon((*next_stmt)->getEndLoc(), context->comp_inst_));

  string mutated_token2{ConvertToString(s, context->comp_inst_->getLangOpts())};
  size_t closing_brace_idx = mutated_token2.find_last_of("}");
  mutated_token2 = mutated_token2.substr(0, closing_brace_idx);
  mutated_token2 += ConvertToString((*next_stmt), 
                                    context->comp_inst_->getLangOpts());

  if (!(isa<CompoundStmt>(*next_stmt) || isa<ForStmt>(*next_stmt) || 
        isa<IfStmt>(*next_stmt) || isa<WhileStmt>(*next_stmt) ||
        isa<SwitchCase>(*next_stmt) || 
        isa<SwitchStmt>(*next_stmt) || isa<LabelStmt>(*next_stmt)))
    mutated_token2 += ";";
  // cout<<"##stmt##"<<endl;
  // s->dump();
  // cout<<"##parent##"<<endl;
  // parent->dump();
  // cout<<"##next##"<<endl;
  // (*next_stmt)->dump();
  // cout<<"########"<<endl;
  if((isa<CaseStmt>(*next_stmt) || isa<DefaultStmt>(*next_stmt))&& isa<CaseStmt>(parent))
    skip_down = true;
  mutated_token2 += "\n}\n";
  if(!skip_down){
    context->mutant_database_.AddMutantEntry(context->getStmtContext(),
      name_, start_loc, end_loc, token, mutated_token2, 
      context->getStmtContext().getProteumStyleLineNum(), "DOWN");
  }
}

void SMVB::collectDeclRefExprs(Stmt const* stmt) {
  if (stmt) {
    if (DeclRefExpr const* dre = dyn_cast<DeclRefExpr>(stmt)) {
      const ValueDecl* decl = dre->getDecl();
      VD_refs.push_back(decl);
    }
    for (const Stmt* childStmt : stmt->children()) {
      collectDeclRefExprs(childStmt);
    }
  }
}

bool SMVB::hasDeclRef(Stmt const* stmt) {

  if (!VD_refs.empty()) {
    // Print or process the collected declarations as needed
    VD_refs.clear();
  }

  collectDeclRefExprs(stmt);

  if (!VD_refs.empty()) {
    // Print or process the collected declarations as needed
    for (const ValueDecl* decl : VD_refs) {
      // decl->dump();
    }
    return true;
  }

  return false;
}

void SMVB::collectVarDeclsBefore(const CompoundStmt* ps, const Stmt* chs) {
  if (!ps || !chs)
    return;
  bool found = false;
  for (const Stmt* stmt : ps->body()) {
    if (stmt == chs) {
      found = true;
      continue;
    }
    if (!found) {
      if (const DeclStmt* declStmt = dyn_cast<DeclStmt>(stmt)) {
        // Collect the VarDecl nodes from the DeclStmt
        for (DeclStmt::const_decl_iterator it = declStmt->decl_begin(); it != declStmt->decl_end(); ++it) {
          if (const ValueDecl* varDecl = dyn_cast<ValueDecl>(*it)) {
            VDs.push_back(varDecl);
          }
        }
      }
    }
  }
}
